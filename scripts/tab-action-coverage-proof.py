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

REQUIRED_TABS = ["recon", "web", "network", "creds", "exploit", "post", "osint", "report", "stash"]

REQUIRED_CONTRACTS = {
    "reconCopyActions",
    "webDirectActions",
    "webRowContextActions",
    "webVerifyAction",
    "networkProtocolAction",
    "networkCopyActions",
    "credsActionResults",
    "credsCopyActions",
    "exploitActionStages",
    "exploitCopyActions",
    "postAttribution",
    "postCopyActions",
    "osintCopyActions",
    "osintArtifactActions",
    "reportGenerateAction",
    "reportFindingActions",
    "reportVisibleDeleteWiring",
    "reportExportActions",
    "reportAgentAction",
    "stashActions",
    "stashRowContextActions",
    "stashAddSheet",
    "stashSendChatControl",
}

REQUIRED_ROUTES = {
    "/qa/seed-recon-action-status",
    "/qa/seed-recon-copy-actions",
    "/qa/recon-copy",
    "/qa/seed-web-direct-actions",
    "/qa/web-create-finding",
    "/qa/web-stash",
    "/qa/web-copy",
    "/qa/web-copy-all",
    "/qa/web-row-action",
    "/qa/web-search-related",
    "/qa/seed-web-verify-action",
    "/qa/seed-network-protocol-action",
    "/qa/seed-network-copy-actions",
    "/qa/network-copy",
    "/qa/seed-creds-action-results",
    "/qa/seed-creds-copy-actions",
    "/qa/creds-copy",
    "/qa/seed-exploit-action-differentiation",
    "/qa/seed-exploit-copy-actions",
    "/qa/exploit-copy",
    "/qa/seed-post-attribution",
    "/qa/seed-post-copy-actions",
    "/qa/post-copy",
    "/qa/seed-osint-screenshot-artifact",
    "/qa/seed-osint-copy-actions",
    "/qa/osint-copy",
    "/qa/osint-artifact-action",
    "/qa/seed-report-export",
    "/qa/seed-report-generate-action",
    "/qa/report-generate-action",
    "/qa/seed-report-agent-action",
    "/qa/seed-report-finding-actions",
    "/qa/report-create-finding",
    "/qa/report-submit-finding",
    "/qa/report-delete-finding",
    "/qa/report-export-action",
    "/qa/seed-stash-actions",
    "/qa/stash-add",
    "/qa/stash-add-sheet",
    "/qa/stash-filter",
    "/qa/stash-copy-all",
    "/qa/stash-copy",
    "/qa/stash-row-action",
    "/qa/stash-send",
    "/qa/stash-delete",
}

REQUIRED_PROOFS = {
    "recon-action-status-proof.py",
    "recon-copy-actions-proof.py",
    "web-direct-actions-proof.py",
    "web-header-copy-proof.py",
    "web-row-context-actions-proof.py",
    "web-verify-action-proof.py",
    "network-protocol-action-proof.py",
    "network-copy-actions-proof.py",
    "creds-action-results-proof.py",
    "creds-copy-actions-proof.py",
    "exploit-action-differentiation-proof.py",
    "exploit-copy-actions-proof.py",
    "post-attribution-proof.py",
    "post-copy-actions-proof.py",
    "osint-copy-actions-proof.py",
    "osint-screenshot-artifact-proof.py",
    "osint-artifact-actions-proof.py",
    "report-generate-action-proof.py",
    "report-finding-actions-proof.py",
    "report-visible-delete-wiring-proof.py",
    "report-export-proof.py",
    "report-visible-export-actions-proof.py",
    "report-agent-action-proof.py",
    "stash-actions-proof.py",
    "stash-row-context-actions-proof.py",
    "stash-add-sheet-proof.py",
    "stash-send-chat-control-proof.py",
}

REQUIRED_ACTION_STATE_KEYS = {
    "tabActivities",
    "webAction",
    "webDirectActions",
    "reconAction",
    "reconCopyActions",
    "networkAction",
    "networkCopyActions",
    "networkLifecycle",
    "credsAction",
    "credsCopyActions",
    "credsLifecycle",
    "exploitAction",
    "exploitCopyActions",
    "exploitActionHistory",
    "exploitLifecycle",
    "postLifecycle",
    "postAttribution",
    "postCopyActions",
    "osintLifecycle",
    "osintArtifactAction",
    "osintCopyActions",
    "reportExport",
    "reportAction",
    "reportRenderActions",
    "reportFindingActions",
    "stashActions",
}

REQUIRED_ACTION_SURFACES = [
    "reconActions",
    "webActions",
    "networkActions",
    "credsActions",
    "exploitActions",
    "postActions",
    "osintActions",
    "reportActions",
    "stashActions",
]

REQUIRED_ACTION_SURFACE_PROOFS = {
    "reconActions": ["recon-action-status-proof.py", "recon-copy-actions-proof.py"],
    "webActions": [
        "web-direct-actions-proof.py",
        "web-header-copy-proof.py",
        "web-row-context-actions-proof.py",
        "web-verify-action-proof.py",
    ],
    "networkActions": ["network-protocol-action-proof.py", "network-copy-actions-proof.py"],
    "credsActions": ["creds-action-results-proof.py", "creds-copy-actions-proof.py"],
    "exploitActions": ["exploit-action-differentiation-proof.py", "exploit-copy-actions-proof.py"],
    "postActions": ["post-attribution-proof.py", "post-copy-actions-proof.py"],
    "osintActions": [
        "osint-copy-actions-proof.py",
        "osint-screenshot-artifact-proof.py",
        "osint-artifact-actions-proof.py",
    ],
    "reportActions": [
        "report-generate-action-proof.py",
        "report-finding-actions-proof.py",
        "report-visible-delete-wiring-proof.py",
        "report-export-proof.py",
        "report-visible-export-actions-proof.py",
        "report-agent-action-proof.py",
    ],
    "stashActions": [
        "stash-actions-proof.py",
        "stash-row-context-actions-proof.py",
        "stash-add-sheet-proof.py",
        "stash-send-chat-control-proof.py",
    ],
}


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


def assert_tab_action_coverage() -> None:
    state = request("GET", "/state")
    coverage = request("GET", "/qa/tab-action-coverage")

    if coverage.get("ok") is not True:
        raise AssertionError(f"/qa/tab-action-coverage failed: {coverage}")
    if coverage.get("tabs") != REQUIRED_TABS:
        raise AssertionError(f"tab action coverage tabs mismatch: {coverage}")

    contracts = coverage.get("contracts") or {}
    missing_contracts = sorted(name for name in REQUIRED_CONTRACTS if contracts.get(name) is not True)
    if missing_contracts:
        raise AssertionError(f"tab action coverage missing contracts {missing_contracts}: {coverage}")

    routes = set(coverage.get("routes") or [])
    missing_routes = sorted(REQUIRED_ROUTES.difference(routes))
    if missing_routes:
        raise AssertionError(f"tab action coverage missing routes {missing_routes}: {coverage}")

    proofs = set(coverage.get("proofs") or [])
    missing_proofs = sorted(REQUIRED_PROOFS.difference(proofs))
    if missing_proofs:
        raise AssertionError(f"tab action coverage missing proofs {missing_proofs}: {coverage}")
    missing_files = sorted(name for name in REQUIRED_PROOFS if not (ROOT / "scripts" / name).is_file())
    if missing_files:
        raise AssertionError(f"tab action coverage names non-existent proof files: {missing_files}")
    if coverage.get("proofFileParity") is not True:
        raise AssertionError(f"tab action coverage proof file parity mismatch: {coverage}")

    if coverage.get("proofCount", 0) < len(REQUIRED_PROOFS):
        raise AssertionError(f"tab action coverage proof count mismatch: {coverage}")
    if coverage.get("tabActionSurfaces") != REQUIRED_ACTION_SURFACES:
        raise AssertionError(f"tab action coverage surface list mismatch: {coverage}")
    if coverage.get("tabActionSurfaceCount") != len(REQUIRED_ACTION_SURFACES):
        raise AssertionError(f"tab action coverage surface count mismatch: {coverage}")
    if coverage.get("tabActionSurfaceParity") is not True:
        raise AssertionError(f"tab action coverage surface parity mismatch: {coverage}")
    if coverage.get("tabActionSurfaceProofs") != REQUIRED_ACTION_SURFACE_PROOFS:
        raise AssertionError(f"tab action coverage surface proof map mismatch: {coverage}")
    if coverage.get("tabActionSurfaceProofCount") != len(REQUIRED_ACTION_SURFACE_PROOFS):
        raise AssertionError(f"tab action coverage surface proof count mismatch: {coverage}")
    if coverage.get("tabActionSurfaceProofParity") is not True:
        raise AssertionError(f"tab action coverage surface proof parity mismatch: {coverage}")
    for surface, proof_names in REQUIRED_ACTION_SURFACE_PROOFS.items():
        missing_surface_files = sorted(name for name in proof_names if not (ROOT / "scripts" / name).is_file())
        if missing_surface_files:
            raise AssertionError(f"tab action surface {surface} names missing proof files {missing_surface_files}: {coverage}")
    if coverage.get("tabActionSurfaceProofFileParity") is not True:
        raise AssertionError(f"tab action surface proof-file parity mismatch: {coverage}")
    state_keys = set(coverage.get("actionStateKeys") or [])
    missing_state_keys = sorted(REQUIRED_ACTION_STATE_KEYS.difference(state_keys))
    if missing_state_keys:
        raise AssertionError(f"tab action coverage missing state keys {missing_state_keys}: {coverage}")

    qa = state.get("qaCoverage") or {}
    if "/qa/tab-action-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing tab action coverage route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_tab_action_coverage()
        print("tab-action-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"tab-action-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
