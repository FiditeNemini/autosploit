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
    "subtab-lifecycle-matrix-proof.py",
    "subtab-coverage-proof.py",
    "tab-tool-function-flow-proof.py",
    "session-workflow-matrix-proof.py",
    "visual-surface-matrix-proof.py",
    "coverage-index-proof.py",
    "app-qa-matrix-smoke-proof.py",
]


def request(method: str, path: str, body: str | dict | None = None, timeout: float = 45.0):
    if isinstance(body, dict):
        body = json.dumps(body)
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


def expected_rows(subtab_coverage: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for tab in sorted(subtab_coverage.get("tabs") or {}):
        entry = (subtab_coverage.get("tabs") or {}).get(tab) or {}
        for subtab in entry.get("validSubtabs") or []:
            rows.append((tab, subtab))
    return rows


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
        matrix = request("GET", "/qa/subtab-lifecycle-matrix")
        subtab_coverage = request("GET", "/qa/subtab-coverage")
        tab_tool_flow = request("GET", "/qa/tab-tool-function-flow")
        session_workflow = request("GET", "/qa/session-workflow-matrix")
        visual_surface = request("GET", "/qa/visual-surface-matrix")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"subtab lifecycle matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"subtab lifecycle matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"subtab lifecycle matrix proof-file parity mismatch: {matrix}")
        if matrix.get("proofOwnerFileParity") is not True:
            raise AssertionError(f"subtab lifecycle matrix owner parity mismatch: {matrix}")
        if matrix.get("subtabCount") != sum((entry.get("count") or 0) for entry in (subtab_coverage.get("tabs") or {}).values()):
            raise AssertionError(f"subtab lifecycle matrix count mismatch: {matrix}")
        if matrix.get("rowParity") is not True:
            raise AssertionError(f"subtab lifecycle matrix row parity mismatch: {matrix}")
        if matrix.get("tabToolFunctionFlowCount") != tab_tool_flow.get("tabCount"):
            raise AssertionError(f"subtab lifecycle matrix tab flow count mismatch: {matrix}")
        if matrix.get("sessionWorkflowMatrixCount") != session_workflow.get("workflowCount"):
            raise AssertionError(f"subtab lifecycle matrix session workflow count mismatch: {matrix}")
        if matrix.get("visualSurfaceMatrixCount") != visual_surface.get("surfaceCount"):
            raise AssertionError(f"subtab lifecycle matrix visual surface count mismatch: {matrix}")

        rows = matrix.get("subtabRows") or []
        if [(row.get("tab") or "", row.get("subtab") or "") for row in rows] != expected_rows(subtab_coverage):
            raise AssertionError(f"subtab lifecycle matrix row order mismatch: {matrix}")
        for row in rows:
            proofs = row.get("proofs") or []
            if not proofs:
                raise AssertionError(f"subtab row has no proof owner: {row}")
            assert_file_proofs_exist(proofs, row.get("subtab") or "subtab")
            if row.get("proofOwnerExists") is not True:
                raise AssertionError(f"subtab proof owner parity failed: {row}")
            if row.get("subtabCoverageRoute") != "/qa/subtab-coverage":
                raise AssertionError(f"subtab coverage route mismatch: {row}")
            if row.get("tabToolFunctionFlowRoute") != "/qa/tab-tool-function-flow":
                raise AssertionError(f"subtab tab-flow route mismatch: {row}")
            if row.get("sessionWorkflowMatrixRoute") != "/qa/session-workflow-matrix":
                raise AssertionError(f"subtab session workflow route mismatch: {row}")
            if row.get("visualSurfaceMatrixRoute") != "/qa/visual-surface-matrix":
                raise AssertionError(f"subtab visual surface route mismatch: {row}")
            if row.get("route") not in {"/qa/tool-subtab", "/qa/visual-subtab"}:
                raise AssertionError(f"subtab route mismatch: {row}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/subtab-lifecycle-matrix" not in state_routes:
            raise AssertionError(f"state routes missing subtab lifecycle matrix: {state_routes}")

        tabs_group = (index.get("groups") or {}).get("tabsAndSessions") or {}
        if tabs_group.get("subtabLifecycleMatrixCount") != matrix.get("subtabCount"):
            raise AssertionError(f"coverage index subtab lifecycle matrix count mismatch: {index}")
        if tabs_group.get("subtabLifecycleMatrixProofOwnerFileParity") != matrix.get("proofOwnerFileParity"):
            raise AssertionError(f"coverage index subtab lifecycle matrix owner parity mismatch: {index}")
        if tabs_group.get("subtabLifecycleMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index subtab lifecycle matrix proof parity mismatch: {index}")
        if tabs_group.get("subtabLifecycleMatrixTabToolFunctionFlowCount") != matrix.get("tabToolFunctionFlowCount"):
            raise AssertionError(f"coverage index subtab lifecycle matrix tab-flow count mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/subtab-lifecycle-matrix",
            "subtab-lifecycle-matrix-proof.py",
            "subtabLifecycleMatrixCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing subtab lifecycle matrix token {token}")

        print("subtab-lifecycle-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"subtab-lifecycle-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
