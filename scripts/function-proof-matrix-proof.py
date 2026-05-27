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

EXPECTED_GROUP_ROUTES = {
    "appStateActions": "/qa/action-state-inventory",
    "qaAndProofs": "/qa/endpoint-inventory",
    "agentLoop": "/qa/agent-flow-inventory",
    "chatAndContext": "/qa/context-coverage",
    "runtimeAndModels": "/qa/runtime-coverage",
    "settingsAndVisuals": "/qa/settings-coverage",
    "tabAndEvidence": "/qa/tab-action-coverage",
    "servicesAndExecution": "/qa/service-inventory",
    "viewCallbacks": "/qa/view-inventory",
    "support": "/qa/coverage-index",
}
EXPECTED_PROOFS = [
    "function-proof-matrix-proof.py",
    "function-flow-inventory-proof.py",
    "action-state-inventory-proof.py",
    "endpoint-inventory-proof.py",
    "view-inventory-proof.py",
    "service-inventory-proof.py",
    "agent-flow-inventory-proof.py",
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
        matrix = request("GET", "/qa/function-proof-matrix")
        flow = request("GET", "/qa/function-flow-inventory")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"function proof matrix route failed: {matrix}")
        if matrix.get("functionCount") != flow.get("functionCount"):
            raise AssertionError(f"function proof matrix count mismatch: {matrix}")
        if matrix.get("rowParity") is not True:
            raise AssertionError(f"function proof matrix row parity mismatch: {matrix}")
        if matrix.get("groupRouteParity") is not True:
            raise AssertionError(f"function proof matrix group route parity mismatch: {matrix}")
        if matrix.get("proofOwnerFileParity") is not True:
            raise AssertionError(f"function proof matrix proof owner file parity mismatch: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"function proof matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"function proof matrix proof-file parity mismatch: {matrix}")
        if matrix.get("groupRoutes") != EXPECTED_GROUP_ROUTES:
            raise AssertionError(f"function proof matrix group route map mismatch: {matrix}")

        flow_rows = flow.get("functions") or []
        matrix_rows = matrix.get("functions") or []
        if len(matrix_rows) != len(flow_rows):
            raise AssertionError(f"function proof matrix row count mismatch: {matrix}")
        flow_keys = {(row.get("file"), row.get("name"), row.get("group")) for row in flow_rows}
        matrix_keys = {(row.get("file"), row.get("name"), row.get("group")) for row in matrix_rows}
        if matrix_keys != flow_keys:
            raise AssertionError(f"function proof matrix row key mismatch: {matrix}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/function-proof-matrix" not in state_routes:
            raise AssertionError(f"state routes missing function proof matrix: {state_routes}")
        for row in matrix_rows:
            route = row.get("route")
            proof_owner = row.get("proofOwner")
            if route != EXPECTED_GROUP_ROUTES.get(row.get("group")):
                raise AssertionError(f"{row.get('name')} route mismatch: {row}")
            if route not in state_routes:
                raise AssertionError(f"{row.get('name')} route not in state route list: {row}")
            if not (ROOT / "scripts" / proof_owner).is_file():
                raise AssertionError(f"{row.get('name')} proof owner missing on disk: {row}")
            if row.get("proofOwnerExists") is not True:
                raise AssertionError(f"{row.get('name')} proof owner parity mismatch: {row}")

        app_state = (index.get("groups") or {}).get("appState") or {}
        if app_state.get("functionProofMatrixCount") != matrix.get("functionCount"):
            raise AssertionError(f"coverage index function proof matrix count mismatch: {index}")
        if app_state.get("functionProofMatrixRowParity") != matrix.get("rowParity"):
            raise AssertionError(f"coverage index function proof matrix row parity mismatch: {index}")
        if app_state.get("functionProofMatrixGroupRouteParity") != matrix.get("groupRouteParity"):
            raise AssertionError(f"coverage index function proof matrix group route parity mismatch: {index}")
        if app_state.get("functionProofMatrixProofOwnerFileParity") != matrix.get("proofOwnerFileParity"):
            raise AssertionError(f"coverage index function proof matrix owner parity mismatch: {index}")
        if app_state.get("functionProofMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index function proof matrix proof parity mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in ["/qa/function-proof-matrix", "function-proof-matrix-proof.py", "functionProofMatrixCount"]:
            if token not in docs_text:
                raise AssertionError(f"docs missing function proof matrix token {token}")

        print("function-proof-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"function-proof-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
