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
    "session-workflow-matrix-proof.py",
    "session-coverage-proof.py",
    "tab-action-coverage-proof.py",
    "agent-loop-phase-matrix-proof.py",
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
        matrix = request("GET", "/qa/session-workflow-matrix")
        session = request("GET", "/qa/session-coverage")
        tab_action = request("GET", "/qa/tab-action-coverage")
        phase_matrix = request("GET", "/qa/agent-loop-phase-matrix")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"session workflow matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"session workflow matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"session workflow matrix proof-file parity mismatch: {matrix}")
        if matrix.get("proofOwnerFileParity") is not True:
            raise AssertionError(f"session workflow matrix proof owner parity mismatch: {matrix}")
        if matrix.get("workflowCount") != session.get("sessionWorkflowSurfaceCount"):
            raise AssertionError(f"session workflow matrix count mismatch: {matrix}")
        if matrix.get("workflowParity") is not True:
            raise AssertionError(f"session workflow matrix parity mismatch: {matrix}")
        if matrix.get("tabActionRouteCount") != len(tab_action.get("routes") or []):
            raise AssertionError(f"session workflow matrix tab-action route count mismatch: {matrix}")
        if matrix.get("agentLoopPhaseMatrixCount") != phase_matrix.get("phaseCount"):
            raise AssertionError(f"session workflow matrix phase matrix count mismatch: {matrix}")

        rows = matrix.get("workflowRows") or []
        if [row.get("workflow") for row in rows] != session.get("sessionWorkflowSurfaces"):
            raise AssertionError(f"session workflow matrix row order mismatch: {matrix}")
        for row in rows:
            workflow = row.get("workflow")
            proofs = row.get("proofs") or []
            routes = row.get("routes") or []
            state_keys = row.get("stateKeys") or []
            if proofs != (session.get("sessionWorkflowSurfaceProofs") or {}).get(workflow):
                raise AssertionError(f"{workflow} proof map mismatch: {row}")
            assert_file_proofs_exist(proofs, workflow or "workflow")
            if row.get("proofOwnerExists") is not True:
                raise AssertionError(f"{workflow} proof owner parity failed: {row}")
            if row.get("sessionCoverageRoute") != "/qa/session-coverage":
                raise AssertionError(f"{workflow} session route mismatch: {row}")
            if row.get("tabActionCoverageRoute") != "/qa/tab-action-coverage":
                raise AssertionError(f"{workflow} tab-action route mismatch: {row}")
            if row.get("agentLoopPhaseMatrixRoute") != "/qa/agent-loop-phase-matrix":
                raise AssertionError(f"{workflow} agent phase matrix route mismatch: {row}")
            if not routes:
                raise AssertionError(f"{workflow} has no route owners: {row}")
            if not state_keys:
                raise AssertionError(f"{workflow} has no state key owners: {row}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/session-workflow-matrix" not in state_routes:
            raise AssertionError(f"state routes missing session workflow matrix: {state_routes}")

        tabs_sessions = (index.get("groups") or {}).get("tabsAndSessions") or {}
        if tabs_sessions.get("sessionWorkflowMatrixCount") != matrix.get("workflowCount"):
            raise AssertionError(f"coverage index session workflow matrix count mismatch: {index}")
        if tabs_sessions.get("sessionWorkflowMatrixProofOwnerFileParity") != matrix.get("proofOwnerFileParity"):
            raise AssertionError(f"coverage index session workflow matrix owner parity mismatch: {index}")
        if tabs_sessions.get("sessionWorkflowMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index session workflow matrix proof parity mismatch: {index}")
        if tabs_sessions.get("sessionWorkflowMatrixTabActionRouteCount") != matrix.get("tabActionRouteCount"):
            raise AssertionError(f"coverage index session workflow matrix tab-action count mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/session-workflow-matrix",
            "session-workflow-matrix-proof.py",
            "sessionWorkflowMatrixCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing session workflow matrix token {token}")

        print("session-workflow-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"session-workflow-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
