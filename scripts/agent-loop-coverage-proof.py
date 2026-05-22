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

EXPECTED_MODES = {
    "autopilot": "execute",
    "copilot": "approval",
    "manual": "suggest",
}
EXPECTED_PROOFS = {
    "live-turn-harness.py",
    "mode-selection-flow-proof.py",
    "tool-fanout-status-proof.py",
    "agent-autopilot-proof.py",
    "agent-search-context-proof.py",
    "agent-actions-proof.py",
    "agent-deploy-sheet-proof.py",
    "agent-deploy-task-send-proof.py",
    "agent-settings-actions-proof.py",
}

EXPECTED_ROUTES = {
    "/mode",
    "/qa/deploy-agent",
    "/qa/seed-agent-actions",
    "/qa/agent-action",
    "/qa/agent-deploy-sheet",
    "/qa/agent-settings-action",
    "/qa/apply-app-settings",
}

EXPECTED_CONTRACTS = {
    "manualModeSuggests",
    "copilotModeRequiresApproval",
    "autopilotModeExecutes",
    "deployedAgentsForceAutopilot",
    "agentRuntimeInheritance",
    "agentGenerationDefaultsInheritance",
    "agentReasoningInheritance",
    "agentMaxIterationsInheritance",
    "agentSearchContextTool",
    "agentDeploySheet",
    "agentTaskSend",
    "agentSettingsControls",
}

EXPECTED_ACTION_TELEMETRY_FIELDS = {
    "status",
    "lastAction",
    "agentId",
    "agentName",
    "agentType",
    "agentCount",
    "deploySheetVisible",
    "taskSent",
    "messageCount",
    "stoppedGeneration",
    "summary",
}

EXPECTED_STATE_KEYS = {
    "agents",
    "agentActions",
    "displayChatService",
    "displayResultsStore",
    "displayActivityFeed",
    "chatService.interactionMode",
    "chatService.maxIterations",
    "chatService.lastContextSnippetCount",
    "chatService.lastToolSchemaNames",
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


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        coverage = request("GET", "/qa/agent-loop-coverage")
        if coverage.get("ok") is not True:
            raise AssertionError(f"agent loop coverage route failed: {coverage}")
        if coverage.get("modes") != EXPECTED_MODES:
            raise AssertionError(f"mode behavior contract mismatch: {coverage}")
        if coverage.get("currentMode") not in EXPECTED_MODES:
            raise AssertionError(f"current mode missing from contract: {coverage}")
        if coverage.get("maxIterations", 0) < 1:
            raise AssertionError(f"max iterations not surfaced: {coverage}")

        agent_contract = coverage.get("agents") or {}
        if agent_contract.get("forcedMode") != "autopilot":
            raise AssertionError(f"agent forced mode contract missing: {coverage}")
        for key in ("inheritsEngine", "inheritsGenerationDefaults", "inheritsReasoning", "inheritsMaxIterations", "searchContextTool"):
            if agent_contract.get(key) is not True:
                raise AssertionError(f"agent contract missing {key}: {coverage}")

        proofs = set(coverage.get("proofs") or [])
        missing = sorted(EXPECTED_PROOFS.difference(proofs))
        if missing:
            raise AssertionError(f"agent loop proofs missing {missing}: {coverage}")
        missing_files = sorted(name for name in EXPECTED_PROOFS if not (ROOT / "scripts" / name).is_file())
        if missing_files:
            raise AssertionError(f"agent loop names non-existent proof files: {missing_files}")

        routes = set(coverage.get("routes") or [])
        missing_routes = sorted(EXPECTED_ROUTES.difference(routes))
        if missing_routes:
            raise AssertionError(f"agent loop routes missing {missing_routes}: {coverage}")

        contracts = coverage.get("contracts") or {}
        missing_contracts = sorted(name for name in EXPECTED_CONTRACTS if contracts.get(name) is not True)
        if missing_contracts:
            raise AssertionError(f"agent loop contracts missing {missing_contracts}: {coverage}")
        if coverage.get("proofCount", 0) < len(EXPECTED_PROOFS):
            raise AssertionError(f"agent loop proof count mismatch: {coverage}")
        telemetry_fields = set(coverage.get("actionTelemetryFields") or [])
        missing_telemetry = sorted(EXPECTED_ACTION_TELEMETRY_FIELDS.difference(telemetry_fields))
        if missing_telemetry:
            raise AssertionError(f"agent loop telemetry fields missing {missing_telemetry}: {coverage}")
        state_keys = set(coverage.get("stateKeys") or [])
        missing_state_keys = sorted(EXPECTED_STATE_KEYS.difference(state_keys))
        if missing_state_keys:
            raise AssertionError(f"agent loop state keys missing {missing_state_keys}: {coverage}")
        if coverage.get("stateKeyCount") != len(coverage.get("stateKeys") or []):
            raise AssertionError(f"agent loop state key count mismatch: {coverage}")
        visual_state_keys = set(coverage.get("visualStateKeys") or [])
        for key in ("agents", "agentActions", "displayChatService", "displayResultsStore", "displayActivityFeed"):
            if key not in visual_state_keys:
                raise AssertionError(f"agent loop visual state key missing {key}: {coverage}")

        request("POST", "/mode", "manual")
        manual = request("GET", "/qa/agent-loop-coverage")
        if manual.get("currentMode") != "manual":
            raise AssertionError(f"agent loop coverage did not reflect manual mode: {manual}")

        print("agent-loop-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"agent-loop-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
