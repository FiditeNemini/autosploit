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
ROUTE = "/qa/live-status-preview-flow"

EXPECTED_FLOWS = [
    "toolStatusIndicator",
    "agentStatusLine",
    "activityLogTelemetry",
    "resultPreviewParser",
    "stashPreviewContextHandoff",
    "reportFindingTrackManagement",
    "evidenceLifecycleHandoff",
]


def request(method: str, path: str, timeout: float = 45.0):
    req = urllib.request.Request(f"{APP_API}{path}", method=method)
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


def assert_payload(payload: dict, state: dict, index: dict) -> None:
    if payload.get("ok") is not True:
        raise AssertionError(f"{ROUTE} failed: {payload}")
    if payload.get("route") != ROUTE:
        raise AssertionError(f"{ROUTE} route mismatch: {payload}")
    if payload.get("proofLevel") != "user-facing-live-status-log-preview-flow":
        raise AssertionError(f"{ROUTE} proof level mismatch: {payload}")
    if payload.get("flowIds") != EXPECTED_FLOWS:
        raise AssertionError(f"{ROUTE} flow order mismatch: {payload}")
    if payload.get("flowCount") != len(EXPECTED_FLOWS):
        raise AssertionError(f"{ROUTE} flow count mismatch: {payload}")
    if payload.get("readyFlowCount") != len(EXPECTED_FLOWS):
        raise AssertionError(f"{ROUTE} should have every flow ready: {payload}")
    if payload.get("blockedFlowIds"):
        raise AssertionError(f"{ROUTE} should not have blocked flows: {payload}")
    if payload.get("contractParity") is not True:
        raise AssertionError(f"{ROUTE} contract parity mismatch: {payload}")
    if payload.get("routeParity") is not True:
        raise AssertionError(f"{ROUTE} route parity mismatch: {payload}")
    if payload.get("proofFileParity") is not True:
        raise AssertionError(f"{ROUTE} proof parity mismatch: {payload}")

    rows = {row.get("id"): row for row in payload.get("rows") or []}
    if set(rows) != set(EXPECTED_FLOWS):
        raise AssertionError(f"{ROUTE} row IDs mismatch: {payload}")
    for flow_id in EXPECTED_FLOWS:
        row = rows.get(flow_id) or {}
        if row.get("status") != "ready":
            raise AssertionError(f"{ROUTE} flow not ready {flow_id}: {row}")
        if row.get("contractOK") is not True:
            raise AssertionError(f"{ROUTE} contract failed {flow_id}: {row}")
        if row.get("routeParity") is not True:
            raise AssertionError(f"{ROUTE} route parity failed {flow_id}: {row}")
        if row.get("proofFileParity") is not True:
            raise AssertionError(f"{ROUTE} proof parity failed {flow_id}: {row}")

    status = rows["toolStatusIndicator"]
    if status.get("indicatorContract") != "status-dot-running-ring":
        raise AssertionError(f"{ROUTE} tab indicator contract mismatch: {status}")
    if status.get("statuses") != ["running", "done", "failed", "canceled"]:
        raise AssertionError(f"{ROUTE} status list mismatch: {status}")
    if not {"activityFeedStatus", "tabStatusIndicator", "chatToolCard"}.issubset(set(status.get("visualSurfaces") or [])):
        raise AssertionError(f"{ROUTE} visual status surfaces missing: {status}")

    agent = rows["agentStatusLine"]
    if "agentLiveToolStatus" not in (agent.get("contracts") or {}):
        raise AssertionError(f"{ROUTE} agent status contract missing: {agent}")
    if not {"status", "lastAction", "summary"}.issubset(set(agent.get("telemetryFields") or [])):
        raise AssertionError(f"{ROUTE} agent telemetry fields missing: {agent}")

    activity = rows["activityLogTelemetry"]
    if "activityFeed" not in (activity.get("storageTargets") or []):
        raise AssertionError(f"{ROUTE} activity storage target missing: {activity}")
    if "activityTelemetry" not in (activity.get("agentFlowPhases") or []):
        raise AssertionError(f"{ROUTE} activity telemetry phase missing: {activity}")

    parser = rows["resultPreviewParser"]
    if parser.get("structuredParsedToolCount", 0) < 10:
        raise AssertionError(f"{ROUTE} structured parser coverage too low: {parser}")
    if parser.get("resultModeCountParity") is not True:
        raise AssertionError(f"{ROUTE} result mode parity mismatch: {parser}")

    stash = rows["stashPreviewContextHandoff"]
    if not {"manualAdd", "sendToChat", "rowContextActions", "dynamicContextCatalog"}.issubset(set(stash.get("surfaces") or [])):
        raise AssertionError(f"{ROUTE} stash surfaces missing: {stash}")
    if "/qa/stash-send" not in (stash.get("routes") or []):
        raise AssertionError(f"{ROUTE} stash send route missing: {stash}")

    report = rows["reportFindingTrackManagement"]
    if not {"findingCrud", "reportPreview", "artifactExport", "agentDraft"}.issubset(set(report.get("surfaces") or [])):
        raise AssertionError(f"{ROUTE} report surfaces missing: {report}")
    if "findings" not in (report.get("stateKeys") or []):
        raise AssertionError(f"{ROUTE} report finding state missing: {report}")

    lifecycle = rows["evidenceLifecycleHandoff"]
    if not {"toolOutputToParser", "parserToResultsTab", "findingToReportPreview", "stashToChatHandoff"}.issubset(set(lifecycle.get("handoffs") or [])):
        raise AssertionError(f"{ROUTE} lifecycle handoffs missing: {lifecycle}")
    if lifecycle.get("handoffCount", 0) < 10:
        raise AssertionError(f"{ROUTE} lifecycle handoff count too low: {lifecycle}")

    state_routes = ((state.get("qaCoverage") or {}).get("stateRoutes") or [])
    if ROUTE not in state_routes:
        raise AssertionError(f"/state qaCoverage missing {ROUTE}: {state.get('qaCoverage')}")

    groups = index.get("groups") or {}
    tools_group = groups.get("toolsAndParsers") or {}
    tabs_group = groups.get("tabsAndSessions") or {}
    for group_name, group in [("toolsAndParsers", tools_group), ("tabsAndSessions", tabs_group)]:
        if ROUTE not in (group.get("endpoints") or []):
            raise AssertionError(f"/qa/coverage-index {group_name} missing {ROUTE}: {group}")
        if "live-status-preview-flow-proof.py" not in (group.get("proofs") or []):
            raise AssertionError(f"/qa/coverage-index {group_name} missing proof: {group}")
    if tools_group.get("liveStatusPreviewFlowIds") != payload.get("flowIds"):
        raise AssertionError(f"/qa/coverage-index tool flow IDs mismatch: {tools_group}")
    if tools_group.get("liveStatusPreviewContractParity") != payload.get("contractParity"):
        raise AssertionError(f"/qa/coverage-index tool contract parity mismatch: {tools_group}")
    if tabs_group.get("liveStatusPreviewReadyFlowCount") != payload.get("readyFlowCount"):
        raise AssertionError(f"/qa/coverage-index tab ready count mismatch: {tabs_group}")
    if tabs_group.get("liveStatusPreviewProofFileParity") != payload.get("proofFileParity"):
        raise AssertionError(f"/qa/coverage-index tab proof parity mismatch: {tabs_group}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        seeded = request("POST", "/qa/seed-result-parser-fixture", timeout=20.0)
        if seeded.get("ok") is not True:
            raise AssertionError(f"result parser fixture seed failed: {seeded}")
        payload = request("GET", ROUTE, timeout=45.0)
        state = request("GET", "/state")
        index = request("GET", "/qa/coverage-index", timeout=120.0)
        assert_payload(payload, state, index)
        print("live-status-preview-flow proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"live-status-preview-flow proof failed: {exc}", flush=True)
        raise SystemExit(1)
