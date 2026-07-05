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

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
ARTIFACT = ROOT / "docs" / "live-proofs" / "2026-07-05-subtab-lifecycle-matrix.json"
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


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def process_evidence() -> dict:
    output = subprocess.check_output(["ps", "-axo", "pid,rss,comm,args"], text=True)
    app_rows: list[str] = []
    engine_rows: list[str] = []
    engine_tokens = (
        "ExploitBotEngine/launch.py",
        "vmlx_engine.server",
        "mlx_server",
        "Qwen3.6",
        "MiniMax-M",
    )
    for line in output.splitlines():
        parts = line.split(None, 3)
        comm = parts[2] if len(parts) >= 3 else ""
        args = parts[3] if len(parts) >= 4 else ""
        if "ExploitBot.app/Contents/MacOS/ExploitBot" in line:
            app_rows.append(line.strip())
        shell_or_watcher = comm.endswith(("/zsh", "/bash", "/sh")) or "/.claude/" in args
        if not shell_or_watcher and any(token in line for token in engine_tokens):
            engine_rows.append(line.strip())
    return {
        "appRows": app_rows,
        "engineProcessRows": engine_rows,
    }


def write_artifact(
    state: dict,
    matrix: dict,
    index: dict,
) -> None:
    tabs_group = (index.get("groups") or {}).get("tabsAndSessions") or {}
    state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
    model_inference_started = bool(state.get("engineRunning")) or bool(state.get("enginePort"))
    report = {
        "ok": True,
        "proofType": "subtab-lifecycle-matrix-live-route",
        "generatedAt": timestamp(),
        "sourceRoute": "/qa/subtab-lifecycle-matrix",
        "status": {
            "currentSourceBuild": "PASS",
            "routeParity": "PASS" if matrix.get("rowParity") is True else "FAIL",
            "proofFileParity": "PASS" if matrix.get("proofFileParity") is True else "FAIL",
            "proofOwnerFileParity": "PASS" if matrix.get("proofOwnerFileParity") is True else "FAIL",
            "modelInferenceStarted": "YES" if model_inference_started else "NO",
        },
        "subtabCount": matrix.get("subtabCount"),
        "subtabRows": matrix.get("subtabRows") or [],
        "proofs": matrix.get("proofs") or [],
        "routeCounts": {
            "tabToolFunctionFlowCount": matrix.get("tabToolFunctionFlowCount"),
            "sessionWorkflowMatrixCount": matrix.get("sessionWorkflowMatrixCount"),
            "visualSurfaceMatrixCount": matrix.get("visualSurfaceMatrixCount"),
            "coverageIndexSubtabLifecycleMatrixCount": tabs_group.get("subtabLifecycleMatrixCount"),
        },
        "routes": {
            "stateRoutePresent": "/qa/subtab-lifecycle-matrix" in state_routes,
            "subtabCoverageRoute": matrix.get("subtabCoverageRoute"),
            "tabToolFunctionFlowRoute": matrix.get("tabToolFunctionFlowRoute"),
            "sessionWorkflowMatrixRoute": matrix.get("sessionWorkflowMatrixRoute"),
            "visualSurfaceMatrixRoute": matrix.get("visualSurfaceMatrixRoute"),
        },
        "stateEvidence": {
            "engineRunning": bool(state.get("engineRunning")),
            "enginePort": state.get("enginePort"),
            "healthStatus": state.get("healthStatus"),
            "activeSubtabs": state.get("activeSubtabs") or {},
        },
        "processEvidence": process_evidence(),
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    env["EXPLOITBOT_SKIP_APP_PROOF_LOCK"] = "1"
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
        index = request("GET", "/qa/coverage-index", timeout=120.0)

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

        write_artifact(state=state, matrix=matrix, index=index)
        print(f"subtab-lifecycle-matrix proof passed and wrote {ARTIFACT}")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        with app_proof_lock("subtab-lifecycle-matrix-proof.py"):
            run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"subtab-lifecycle-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
