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

REQUIRED_CONTRACTS = {
    "onboardingModeSelection",
    "sidebarModeSelection",
    "pendingApprovalRejection",
    "sidebarCrudActions",
    "sidebarCreateStopsRunningGeneration",
    "windowOverlayActions",
    "modelFolderPicker",
    "onboardingModelPicker",
    "persistenceRelaunch",
    "messageSave",
    "resultRebuild",
    "findingWizardSubmit",
    "tabSwitchActions",
    "phaseActions",
    "activityFeedActions",
}

REQUIRED_ROUTES = {
    "/qa/onboarding-complete",
    "/qa/sidebar-mode",
    "/qa/seed-pending-approval",
    "/qa/seed-sidebar-actions",
    "/qa/seed-sidebar-running-create",
    "/qa/sidebar-action",
    "/qa/seed-window-overlay-actions",
    "/qa/window-overlay-action",
    "/qa/model-folder-picker",
    "/qa/onboarding-model-picker",
    "/qa/seed-persistence-fixture",
    "/qa/save-current-messages",
    "/qa/finding-wizard-submit",
    "/qa/manual-tab-switch",
    "/phase",
    "/qa/seed-activity-actions",
    "/qa/activity-action",
}

REQUIRED_PROOFS = {
    "mode-selection-flow-proof.py",
    "sidebar-actions-proof.py",
    "sidebar-create-stops-proof.py",
    "window-overlay-actions-proof.py",
    "model-folder-picker-proof.py",
    "onboarding-model-picker-proof.py",
    "persistence-proof.py",
    "finding-wizard-submit-proof.py",
    "tab-switch-action-proof.py",
    "phase-action-proof.py",
    "activity-feed-actions-proof.py",
}

REQUIRED_STATE_KEYS = {
    "modeSelection",
    "modelFolderInfo",
    "modelFolderPicker",
    "windowOverlayActions",
    "tabSwitchActions",
    "subtabActions",
    "phaseActions",
    "sidebarActions",
    "activityFeedActions",
    "chatControlActions",
    "activeSubtabs",
    "feedRecent",
}

REQUIRED_WORKFLOW_SURFACES = [
    "onboardingModeSelection",
    "sidebarOperationLifecycle",
    "windowOverlayControls",
    "modelFolderSelection",
    "persistenceAndResultRebuild",
    "findingWizardSubmit",
    "tabAndPhaseNavigation",
    "activityFeedControls",
]

REQUIRED_WORKFLOW_SURFACE_PROOFS = {
    "onboardingModeSelection": ["mode-selection-flow-proof.py", "onboarding-model-picker-proof.py"],
    "sidebarOperationLifecycle": ["sidebar-actions-proof.py", "sidebar-create-stops-proof.py"],
    "windowOverlayControls": ["window-overlay-actions-proof.py"],
    "modelFolderSelection": ["model-folder-picker-proof.py", "onboarding-model-picker-proof.py"],
    "persistenceAndResultRebuild": ["persistence-proof.py"],
    "findingWizardSubmit": ["finding-wizard-submit-proof.py"],
    "tabAndPhaseNavigation": ["tab-switch-action-proof.py", "phase-action-proof.py"],
    "activityFeedControls": ["activity-feed-actions-proof.py"],
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


def assert_session_coverage() -> None:
    state = request("GET", "/state")
    coverage = request("GET", "/qa/session-coverage")

    if coverage.get("ok") is not True:
        raise AssertionError(f"/qa/session-coverage failed: {coverage}")

    contracts = coverage.get("contracts") or {}
    missing_contracts = sorted(name for name in REQUIRED_CONTRACTS if contracts.get(name) is not True)
    if missing_contracts:
        raise AssertionError(f"session coverage missing contracts {missing_contracts}: {coverage}")

    routes = set(coverage.get("routes") or [])
    missing_routes = sorted(REQUIRED_ROUTES.difference(routes))
    if missing_routes:
        raise AssertionError(f"session coverage missing routes {missing_routes}: {coverage}")

    proofs = set(coverage.get("proofs") or [])
    missing_proofs = sorted(REQUIRED_PROOFS.difference(proofs))
    if missing_proofs:
        raise AssertionError(f"session coverage missing proofs {missing_proofs}: {coverage}")
    missing_files = sorted(name for name in REQUIRED_PROOFS if not (ROOT / "scripts" / name).is_file())
    if missing_files:
        raise AssertionError(f"session coverage names non-existent proof files: {missing_files}")
    if coverage.get("proofFileParity") is not True:
        raise AssertionError(f"session coverage proof file parity mismatch: {coverage}")

    if coverage.get("interactionModes") != ["autopilot", "copilot", "manual"]:
        raise AssertionError(f"session coverage mode order mismatch: {coverage}")
    if coverage.get("overlayActions") != ["toggleTerminal", "closeTerminal", "openSettings", "closeSettings", "openFindingWizard", "dismissFindingWizard"]:
        raise AssertionError(f"session coverage overlay actions mismatch: {coverage}")
    if coverage.get("sidebarActions") != ["createOp", "renameOp", "switchOp", "deleteOp"]:
        raise AssertionError(f"session coverage sidebar actions mismatch: {coverage}")
    if coverage.get("sessionWorkflowSurfaces") != REQUIRED_WORKFLOW_SURFACES:
        raise AssertionError(f"session coverage workflow surfaces mismatch: {coverage}")
    if coverage.get("sessionWorkflowSurfaceCount") != len(REQUIRED_WORKFLOW_SURFACES):
        raise AssertionError(f"session coverage workflow surface count mismatch: {coverage}")
    if coverage.get("sessionWorkflowSurfaceParity") is not True:
        raise AssertionError(f"session coverage workflow surface parity mismatch: {coverage}")
    if coverage.get("sessionWorkflowSurfaceProofs") != REQUIRED_WORKFLOW_SURFACE_PROOFS:
        raise AssertionError(f"session coverage workflow surface proof map mismatch: {coverage}")
    if coverage.get("sessionWorkflowSurfaceProofCount") != len(REQUIRED_WORKFLOW_SURFACE_PROOFS):
        raise AssertionError(f"session coverage workflow surface proof count mismatch: {coverage}")
    if coverage.get("sessionWorkflowSurfaceProofParity") is not True:
        raise AssertionError(f"session coverage workflow surface proof parity mismatch: {coverage}")
    for surface, proof_names in REQUIRED_WORKFLOW_SURFACE_PROOFS.items():
        missing_surface_files = sorted(name for name in proof_names if not (ROOT / "scripts" / name).is_file())
        if missing_surface_files:
            raise AssertionError(f"session workflow surface {surface} names missing proof files {missing_surface_files}: {coverage}")
    if coverage.get("proofCount", 0) < len(REQUIRED_PROOFS):
        raise AssertionError(f"session coverage proof count mismatch: {coverage}")
    state_keys = set(coverage.get("stateKeys") or [])
    missing_state_keys = sorted(REQUIRED_STATE_KEYS.difference(state_keys))
    if missing_state_keys:
        raise AssertionError(f"session coverage missing state keys {missing_state_keys}: {coverage}")

    qa = state.get("qaCoverage") or {}
    if "/qa/session-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing session coverage route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_session_coverage()
        print("session-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"session-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
