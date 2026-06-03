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
    "service-function-matrix-proof.py",
    "service-inventory-proof.py",
    "function-proof-matrix-proof.py",
    "tool-execution-matrix-proof.py",
    "context-flow-matrix-proof.py",
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


def expected_rows(service_inventory: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for service in service_inventory.get("services") or []:
        for function in service.get("functions") or []:
            rows.append((service.get("file") or "", function))
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
        matrix = request("GET", "/qa/service-function-matrix")
        service = request("GET", "/qa/service-inventory")
        function_matrix = request("GET", "/qa/function-proof-matrix")
        tool_execution = request("GET", "/qa/tool-execution-matrix")
        context_flow = request("GET", "/qa/context-flow-matrix")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"service function matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"service function matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"service function matrix proof-file parity mismatch: {matrix}")
        if matrix.get("proofOwnerFileParity") is not True:
            raise AssertionError(f"service function matrix owner parity mismatch: {matrix}")
        if matrix.get("functionCount") != service.get("functionCount"):
            raise AssertionError(f"service function matrix count mismatch: {matrix}")
        if matrix.get("rowParity") is not True:
            raise AssertionError(f"service function matrix row parity mismatch: {matrix}")
        if matrix.get("functionProofMatrixCount") != function_matrix.get("functionCount"):
            raise AssertionError(f"service function matrix function proof count mismatch: {matrix}")
        if matrix.get("toolExecutionMatrixCount") != tool_execution.get("toolCount"):
            raise AssertionError(f"service function matrix tool execution count mismatch: {matrix}")
        if matrix.get("contextFlowMatrixRetrievalSourceCount") != context_flow.get("retrievalSourceCount"):
            raise AssertionError(f"service function matrix context flow count mismatch: {matrix}")

        rows = matrix.get("functionRows") or []
        expected = expected_rows(service)
        if [(row.get("file") or "", row.get("function") or "") for row in rows] != expected:
            raise AssertionError(f"service function matrix row order mismatch: {matrix}")
        for row in rows:
            proofs = row.get("proofs") or []
            if not proofs:
                raise AssertionError(f"service function row has no proof owners: {row}")
            assert_file_proofs_exist(proofs, row.get("function") or "service-function")
            if row.get("proofOwnerExists") is not True:
                raise AssertionError(f"service function proof owner parity failed: {row}")
            if row.get("serviceInventoryRoute") != "/qa/service-inventory":
                raise AssertionError(f"service function service route mismatch: {row}")
            if row.get("functionProofMatrixRoute") != "/qa/function-proof-matrix":
                raise AssertionError(f"service function function matrix route mismatch: {row}")
            if not row.get("group"):
                raise AssertionError(f"service function group missing: {row}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/service-function-matrix" not in state_routes:
            raise AssertionError(f"state routes missing service function matrix: {state_routes}")

        app_group = (index.get("groups") or {}).get("appState") or {}
        if app_group.get("serviceFunctionMatrixCount") != matrix.get("functionCount"):
            raise AssertionError(f"coverage index service function matrix count mismatch: {index}")
        if app_group.get("serviceFunctionMatrixProofOwnerFileParity") != matrix.get("proofOwnerFileParity"):
            raise AssertionError(f"coverage index service function matrix owner parity mismatch: {index}")
        if app_group.get("serviceFunctionMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index service function matrix proof parity mismatch: {index}")
        if app_group.get("serviceFunctionMatrixFunctionProofCount") != matrix.get("functionProofMatrixCount"):
            raise AssertionError(f"coverage index service function matrix function count mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/service-function-matrix",
            "service-function-matrix-proof.py",
            "serviceFunctionMatrixCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing service function matrix token {token}")

        print("service-function-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"service-function-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
