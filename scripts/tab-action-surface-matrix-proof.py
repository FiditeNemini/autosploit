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
    "tab-action-surface-matrix-proof.py",
    "tab-action-coverage-proof.py",
    "action-state-inventory-proof.py",
    "function-proof-matrix-proof.py",
    "coverage-index-proof.py",
    "app-qa-matrix-smoke-proof.py",
]


def request(method: str, path: str, body: str | None = None, timeout: float = 8.0):
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
        matrix = request("GET", "/qa/tab-action-surface-matrix")
        coverage = request("GET", "/qa/tab-action-coverage")
        action_state = request("GET", "/qa/action-state-inventory")
        function_matrix = request("GET", "/qa/function-proof-matrix")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"tab action surface matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"tab action surface matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"tab action surface matrix proof-file parity mismatch: {matrix}")
        if matrix.get("proofOwnerFileParity") is not True:
            raise AssertionError(f"tab action surface matrix owner parity mismatch: {matrix}")
        if matrix.get("surfaceCount") != coverage.get("tabActionSurfaceCount"):
            raise AssertionError(f"tab action surface matrix count mismatch: {matrix}")
        if matrix.get("surfaceParity") is not True:
            raise AssertionError(f"tab action surface matrix parity mismatch: {matrix}")
        if matrix.get("actionStateCount") != action_state.get("actionStateCount"):
            raise AssertionError(f"tab action surface matrix action-state count mismatch: {matrix}")
        if matrix.get("functionProofMatrixCount") != function_matrix.get("functionCount"):
            raise AssertionError(f"tab action surface matrix function count mismatch: {matrix}")

        rows = matrix.get("surfaceRows") or []
        if [row.get("surface") for row in rows] != coverage.get("tabActionSurfaces"):
            raise AssertionError(f"tab action surface matrix row order mismatch: {matrix}")
        for row in rows:
            surface = row.get("surface")
            proofs = row.get("proofs") or []
            routes = row.get("routes") or []
            state_keys = row.get("actionStateKeys") or []
            tabs = row.get("tabs") or []
            if proofs != (coverage.get("tabActionSurfaceProofs") or {}).get(surface):
                raise AssertionError(f"{surface} proof map mismatch: {row}")
            assert_file_proofs_exist(proofs, surface or "surface")
            if row.get("proofOwnerExists") is not True:
                raise AssertionError(f"{surface} proof owner parity failed: {row}")
            if row.get("tabActionCoverageRoute") != "/qa/tab-action-coverage":
                raise AssertionError(f"{surface} tab action route mismatch: {row}")
            if row.get("actionStateInventoryRoute") != "/qa/action-state-inventory":
                raise AssertionError(f"{surface} action-state route mismatch: {row}")
            if row.get("functionProofMatrixRoute") != "/qa/function-proof-matrix":
                raise AssertionError(f"{surface} function matrix route mismatch: {row}")
            if not routes:
                raise AssertionError(f"{surface} has no route owners: {row}")
            if not state_keys:
                raise AssertionError(f"{surface} has no action-state owners: {row}")
            if not tabs:
                raise AssertionError(f"{surface} has no tab owners: {row}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/tab-action-surface-matrix" not in state_routes:
            raise AssertionError(f"state routes missing tab action surface matrix: {state_routes}")

        tabs_sessions = (index.get("groups") or {}).get("tabsAndSessions") or {}
        if tabs_sessions.get("tabActionSurfaceMatrixCount") != matrix.get("surfaceCount"):
            raise AssertionError(f"coverage index tab action surface matrix count mismatch: {index}")
        if tabs_sessions.get("tabActionSurfaceMatrixProofOwnerFileParity") != matrix.get("proofOwnerFileParity"):
            raise AssertionError(f"coverage index tab action surface matrix owner parity mismatch: {index}")
        if tabs_sessions.get("tabActionSurfaceMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index tab action surface matrix proof parity mismatch: {index}")
        if tabs_sessions.get("tabActionSurfaceMatrixActionStateCount") != matrix.get("actionStateCount"):
            raise AssertionError(f"coverage index tab action surface matrix action-state count mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/tab-action-surface-matrix",
            "tab-action-surface-matrix-proof.py",
            "tabActionSurfaceMatrixCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing tab action surface matrix token {token}")

        print("tab-action-surface-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"tab-action-surface-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
