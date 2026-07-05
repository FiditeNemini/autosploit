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

EXPECTED_POLICIES = {
    "manual": {
        "decision": "suggest",
        "executesWithoutApproval": False,
        "createsPendingApproval": False,
        "terminalStatus": "suggested",
    },
    "copilot": {
        "decision": "pauseForApproval",
        "executesWithoutApproval": False,
        "createsPendingApproval": True,
        "approveAction": "execute",
        "rejectAction": "reject",
        "terminalStatus": "pendingApproval",
    },
    "autopilot": {
        "decision": "execute",
        "executesWithoutApproval": True,
        "createsPendingApproval": False,
        "terminalStatus": "runningOrComplete",
        "explicitToolDeny": True,
        "explicitToolDenyMessage": "\\(toolName) was explicitly disallowed by the latest user prompt.",
        "highRiskAutopilotTools": [
            "arjun",
            "bettercap",
            "chisel",
            "dalfox",
            "feroxbuster",
            "ffuf",
            "hashcat",
            "hydra",
            "impacket",
            "linpeas",
            "masscan",
            "metasploit",
            "msfconsole",
            "netexec",
            "nmap",
            "nxc",
            "pwncat",
            "run_shell",
            "sliver",
            "sqlmap",
            "testssl",
            "testssl.sh",
            "tshark",
            "wpscan",
        ],
    },
}

EXPECTED_ROUTES = {
    "/mode",
    "/send",
    "/messages",
    "/approve",
    "/reject",
    "/qa/seed-pending-approval",
    "/qa/chat-control-action",
    "/qa/agent-tool-authorization-coverage",
}

EXPECTED_STATE_KEYS = {
    "interactionMode",
    "chatService.interactionMode",
    "chatService.pendingApproval",
    "messages.role.approval",
    "messages.role.toolCall",
    "messages.toolStatus",
    "displayActivityFeed",
}

EXPECTED_VISUAL_SURFACES = {
    "approvalCard",
    "approveButton",
    "rejectButton",
    "suggestedToolCard",
    "runningToolCard",
    "rejectedToolCard",
    "completedToolCard",
    "activityFeedToolStatus",
    "tabActivityIndicator",
}

EXPECTED_TRANSITIONS = {
    "manualToolCallBecomesSuggestion",
    "copilotToolCallCreatesPendingApproval",
    "approvePendingToolCallClearsPendingAndExecutes",
    "rejectPendingToolCallClearsPendingAndRecordsRejected",
    "modeSwitchRejectsPendingApproval",
    "stopRejectsPendingApproval",
    "autopilotToolCallExecutesWithinMaxIterations",
}

EXPECTED_PROOFS = {
    "agent-tool-authorization-proof.py",
    "live-turn-harness.py",
    "chat-turn-controls-proof.py",
    "mode-selection-flow-proof.py",
    "agent-loop-coverage-proof.py",
    "tool-fanout-status-proof.py",
    "autopilot-tool-policy-proof.py",
}


def request(method: str, path: str, body: str | dict | None = None, timeout: float = 8.0):
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


def assert_contract(coverage: dict) -> None:
    if coverage.get("ok") is not True:
        raise AssertionError(f"authorization coverage route failed: {coverage}")
    if coverage.get("policies") != EXPECTED_POLICIES:
        raise AssertionError(f"authorization policy map mismatch: {coverage}")
    if coverage.get("policyCount") != len(EXPECTED_POLICIES):
        raise AssertionError(f"authorization policy count mismatch: {coverage}")
    if coverage.get("policyParity") is not True:
        raise AssertionError(f"authorization policy parity mismatch: {coverage}")

    routes = set(coverage.get("routes") or [])
    missing_routes = sorted(EXPECTED_ROUTES.difference(routes))
    if missing_routes:
        raise AssertionError(f"authorization routes missing {missing_routes}: {coverage}")
    if coverage.get("routeCount") != len(EXPECTED_ROUTES):
        raise AssertionError(f"authorization route count mismatch: {coverage}")
    if coverage.get("routeParity") is not True:
        raise AssertionError(f"authorization route parity mismatch: {coverage}")

    state_keys = set(coverage.get("stateKeys") or [])
    missing_state_keys = sorted(EXPECTED_STATE_KEYS.difference(state_keys))
    if missing_state_keys:
        raise AssertionError(f"authorization state keys missing {missing_state_keys}: {coverage}")
    if coverage.get("stateKeyCount") != len(EXPECTED_STATE_KEYS):
        raise AssertionError(f"authorization state-key count mismatch: {coverage}")
    if coverage.get("stateKeyParity") is not True:
        raise AssertionError(f"authorization state-key parity mismatch: {coverage}")

    visual_surfaces = set(coverage.get("visualSurfaces") or [])
    missing_surfaces = sorted(EXPECTED_VISUAL_SURFACES.difference(visual_surfaces))
    if missing_surfaces:
        raise AssertionError(f"authorization visual surfaces missing {missing_surfaces}: {coverage}")
    if coverage.get("visualSurfaceCount") != len(EXPECTED_VISUAL_SURFACES):
        raise AssertionError(f"authorization visual surface count mismatch: {coverage}")
    if coverage.get("visualSurfaceParity") is not True:
        raise AssertionError(f"authorization visual surface parity mismatch: {coverage}")

    transitions = set(coverage.get("transitions") or [])
    missing_transitions = sorted(EXPECTED_TRANSITIONS.difference(transitions))
    if missing_transitions:
        raise AssertionError(f"authorization transitions missing {missing_transitions}: {coverage}")
    if coverage.get("transitionCount") != len(EXPECTED_TRANSITIONS):
        raise AssertionError(f"authorization transition count mismatch: {coverage}")
    if coverage.get("transitionParity") is not True:
        raise AssertionError(f"authorization transition parity mismatch: {coverage}")

    proofs = set(coverage.get("proofs") or [])
    missing_proofs = sorted(EXPECTED_PROOFS.difference(proofs))
    if missing_proofs:
        raise AssertionError(f"authorization proofs missing {missing_proofs}: {coverage}")
    if coverage.get("proofCount") != len(EXPECTED_PROOFS):
        raise AssertionError(f"authorization proof count mismatch: {coverage}")
    if coverage.get("proofFileParity") is not True:
        raise AssertionError(f"authorization proof-file parity mismatch: {coverage}")
    missing_files = sorted(name for name in EXPECTED_PROOFS if not (ROOT / "scripts" / name).is_file())
    if missing_files:
        raise AssertionError(f"authorization names non-existent proof files: {missing_files}")


def assert_pending_snapshot(expected_pending: bool, expected_tool: str = "") -> dict:
    coverage = request("GET", "/qa/agent-tool-authorization-coverage")
    assert_contract(coverage)
    pending = coverage.get("pendingApproval") or {}
    if pending.get("hasPending") is not expected_pending:
        raise AssertionError(f"pending approval state mismatch: {coverage}")
    if expected_pending:
        if pending.get("toolName") != expected_tool:
            raise AssertionError(f"pending approval tool mismatch: {coverage}")
        if pending.get("messageRole") != "approval" or pending.get("messageStatus") != "pending":
            raise AssertionError(f"pending approval visual message mismatch: {coverage}")
        if not pending.get("command", "").startswith("nmap -sV"):
            raise AssertionError(f"pending approval command mismatch: {coverage}")
    return coverage


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

        assert_pending_snapshot(False)

        seeded = request("POST", "/qa/seed-pending-approval")
        if seeded.get("ok") is not True:
            raise AssertionError(f"pending approval seed failed: {seeded}")
        assert_pending_snapshot(True, "nmap")

        approved = request("POST", "/approve")
        if approved.get("ok") is not True:
            raise AssertionError(f"approve route failed: {approved}")
        assert_pending_snapshot(False)

        seeded = request("POST", "/qa/seed-pending-approval")
        if seeded.get("ok") is not True:
            raise AssertionError(f"pending approval re-seed failed: {seeded}")
        assert_pending_snapshot(True, "nmap")

        rejected = request("POST", "/reject")
        if rejected.get("ok") is not True:
            raise AssertionError(f"reject route failed: {rejected}")
        assert_pending_snapshot(False)

        print("agent-tool-authorization proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        with app_proof_lock("agent-tool-authorization-proof.py"):
            run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"agent-tool-authorization proof failed: {exc}", flush=True)
        raise SystemExit(1)
