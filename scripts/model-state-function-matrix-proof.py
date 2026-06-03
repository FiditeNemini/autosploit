#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
DOCS = [
    ROOT / "docs" / "app-system-review-2026-05-21.md",
    ROOT / "docs" / "app-flow-inventory-2026-05-21.md",
]

EXPECTED_PROOFS = [
    "model-state-function-matrix-proof.py",
    "model-state-inventory-proof.py",
    "function-proof-matrix-proof.py",
    "runtime-coverage-proof.py",
    "coverage-index-proof.py",
    "app-qa-matrix-smoke-proof.py",
]


def request(method: str, path: str, body: str | None = None, timeout: float = 45.0):
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def wait_for_app(timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            request("GET", "/state", timeout=1.0)
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"app test server did not become ready: {last_error}")


def assert_file_proofs_exist(proofs: list[str], label: str) -> None:
    missing = [proof for proof in proofs if not (ROOT / "scripts" / proof).is_file()]
    if missing:
        raise AssertionError(f"{label} names missing proof files: {missing}")


def expected_rows(model_state_inventory: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for item in model_state_inventory.get("files") or []:
        for function in item.get("functions") or []:
            rows.append((item.get("file") or "", function))
    return rows


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        state = request("GET", "/state")
        matrix = request("GET", "/qa/model-state-function-matrix")
        model_state = request("GET", "/qa/model-state-inventory")
        function_matrix = request("GET", "/qa/function-proof-matrix")
        runtime = request("GET", "/qa/runtime-coverage")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"model state function matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"model state function matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"model state function matrix proof-file parity mismatch: {matrix}")
        if matrix.get("proofOwnerFileParity") is not True:
            raise AssertionError(f"model state function matrix owner parity mismatch: {matrix}")
        if matrix.get("functionCount") != model_state.get("functionCount"):
            raise AssertionError(f"model state function matrix count mismatch: {matrix}")
        if matrix.get("rowParity") is not True:
            raise AssertionError(f"model state function matrix row parity mismatch: {matrix}")
        if matrix.get("functionProofMatrixCount") != function_matrix.get("functionCount"):
            raise AssertionError(f"model state function matrix function proof count mismatch: {matrix}")
        if matrix.get("runtimeCoverageSupportedFamilyCount") != len(runtime.get("supportedFamilies") or []):
            raise AssertionError(f"model state function matrix runtime model count mismatch: {matrix}")

        rows = matrix.get("functionRows") or []
        expected = expected_rows(model_state)
        if [(row.get("file") or "", row.get("function") or "") for row in rows] != expected:
            raise AssertionError(f"model state function matrix row order mismatch: {matrix}")
        for row in rows:
            proofs = row.get("proofs") or []
            if not proofs:
                raise AssertionError(f"model state function row has no proof owners: {row}")
            assert_file_proofs_exist(proofs, row.get("function") or "model-state-function")
            if row.get("proofOwnerExists") is not True:
                raise AssertionError(f"model state function proof owner parity failed: {row}")
            if row.get("modelStateInventoryRoute") != "/qa/model-state-inventory":
                raise AssertionError(f"model state function inventory route mismatch: {row}")
            if row.get("functionProofMatrixRoute") != "/qa/function-proof-matrix":
                raise AssertionError(f"model state function function matrix route mismatch: {row}")
            if row.get("runtimeCoverageRoute") != "/qa/runtime-coverage":
                raise AssertionError(f"model state function runtime route mismatch: {row}")
            if not row.get("group"):
                raise AssertionError(f"model state function group missing: {row}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/model-state-function-matrix" not in state_routes:
            raise AssertionError(f"state routes missing model state function matrix: {state_routes}")

        app_group = (index.get("groups") or {}).get("appState") or {}
        if app_group.get("modelStateFunctionMatrixCount") != matrix.get("functionCount"):
            raise AssertionError(f"coverage index model state function matrix count mismatch: {index}")
        if app_group.get("modelStateFunctionMatrixProofOwnerFileParity") != matrix.get("proofOwnerFileParity"):
            raise AssertionError(f"coverage index model state function matrix owner parity mismatch: {index}")
        if app_group.get("modelStateFunctionMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index model state function matrix proof parity mismatch: {index}")
        if app_group.get("modelStateFunctionMatrixFunctionProofCount") != matrix.get("functionProofMatrixCount"):
            raise AssertionError(f"coverage index model state function matrix function count mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/model-state-function-matrix",
            "model-state-function-matrix-proof.py",
            "modelStateFunctionMatrixCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing model state function matrix token {token}")

        print("model-state-function-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"model-state-function-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
