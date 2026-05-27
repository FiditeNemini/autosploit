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
    "agent-live-tool-status-proof.py",
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
    "agentBroadToolSchemas",
    "agentUnavailableToolDiscovery",
    "agentDeploySheet",
    "agentTaskSend",
    "agentSettingsControls",
    "agentLiveToolStatus",
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
    "agents.details.statusLine",
    "agents.details.currentToolStatus",
}

EXPECTED_LOOP_PHASES = [
    "receiveUserPrompt",
    "retrieveDynamicContext",
    "selectToolSchemas",
    "streamReasoningAndContent",
    "parseToolCalls",
    "applyModePolicy",
    "enforceScope",
    "executeToolOrBuiltin",
    "parseAndStoreToolResult",
    "reenterModelUntilStopOrMaxIterations",
]

EXPECTED_PHASE_PROOFS = {
    "receiveUserPrompt": ["live-turn-harness.py", "tool-fanout-status-proof.py"],
    "retrieveDynamicContext": ["agent-search-context-proof.py", "live-turn-harness.py"],
    "selectToolSchemas": ["live-turn-harness.py", "agent-autopilot-proof.py"],
    "streamReasoningAndContent": ["live-turn-harness.py", "agent-autopilot-proof.py"],
    "parseToolCalls": ["live-turn-harness.py", "tool-fanout-status-proof.py"],
    "applyModePolicy": ["mode-selection-flow-proof.py", "live-turn-harness.py"],
    "enforceScope": ["live-turn-harness.py"],
    "executeToolOrBuiltin": ["tool-fanout-status-proof.py", "agent-autopilot-proof.py", "agent-live-tool-status-proof.py"],
    "parseAndStoreToolResult": ["tool-fanout-status-proof.py", "result-parser-routing-proof.py"],
    "reenterModelUntilStopOrMaxIterations": ["live-turn-harness.py", "agent-autopilot-proof.py"],
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
        if coverage.get("modeCount") != len(EXPECTED_MODES):
            raise AssertionError(f"mode count mismatch: {coverage}")
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
        if agent_contract.get("includeUnavailableToolSchemas") is not True:
            raise AssertionError(f"agent unavailable tool discovery disabled: {coverage}")
        if agent_contract.get("agentCallableAllRegisteredTools") is not True:
            raise AssertionError(f"agent full tool catalogue contract missing: {coverage}")
        if agent_contract.get("toolSchemaMaxTools", 0) < 30:
            raise AssertionError(f"agent tool schema cap is still too narrow: {coverage}")
        if agent_contract.get("fullToolSchemaCount") != agent_contract.get("toolSchemaMaxTools"):
            raise AssertionError(f"agent tool schema cap does not match full catalogue: {coverage}")
        if coverage.get("agentContractCount") != len(agent_contract):
            raise AssertionError(f"agent contract count mismatch: {coverage}")

        proofs = set(coverage.get("proofs") or [])
        missing = sorted(EXPECTED_PROOFS.difference(proofs))
        if missing:
            raise AssertionError(f"agent loop proofs missing {missing}: {coverage}")
        missing_files = sorted(name for name in EXPECTED_PROOFS if not (ROOT / "scripts" / name).is_file())
        if missing_files:
            raise AssertionError(f"agent loop names non-existent proof files: {missing_files}")
        if coverage.get("proofFileParity") is not True:
            raise AssertionError(f"agent loop proof file parity mismatch: {coverage}")

        routes = set(coverage.get("routes") or [])
        missing_routes = sorted(EXPECTED_ROUTES.difference(routes))
        if missing_routes:
            raise AssertionError(f"agent loop routes missing {missing_routes}: {coverage}")
        if coverage.get("routeCount") != len(EXPECTED_ROUTES):
            raise AssertionError(f"agent loop route count mismatch: {coverage}")
        if coverage.get("routeParity") is not True:
            raise AssertionError(f"agent loop route parity mismatch: {coverage}")

        contracts = coverage.get("contracts") or {}
        missing_contracts = sorted(name for name in EXPECTED_CONTRACTS if contracts.get(name) is not True)
        if missing_contracts:
            raise AssertionError(f"agent loop contracts missing {missing_contracts}: {coverage}")
        if coverage.get("contractCount") != len(EXPECTED_CONTRACTS):
            raise AssertionError(f"agent loop contract count mismatch: {coverage}")
        if coverage.get("contractParity") is not True:
            raise AssertionError(f"agent loop contract parity mismatch: {coverage}")
        if coverage.get("proofCount", 0) < len(EXPECTED_PROOFS):
            raise AssertionError(f"agent loop proof count mismatch: {coverage}")
        telemetry_fields = set(coverage.get("actionTelemetryFields") or [])
        missing_telemetry = sorted(EXPECTED_ACTION_TELEMETRY_FIELDS.difference(telemetry_fields))
        if missing_telemetry:
            raise AssertionError(f"agent loop telemetry fields missing {missing_telemetry}: {coverage}")
        if coverage.get("actionTelemetryFieldCount") != len(EXPECTED_ACTION_TELEMETRY_FIELDS):
            raise AssertionError(f"agent loop telemetry field count mismatch: {coverage}")
        if coverage.get("actionTelemetryFieldParity") is not True:
            raise AssertionError(f"agent loop telemetry field parity mismatch: {coverage}")
        state_keys = set(coverage.get("stateKeys") or [])
        missing_state_keys = sorted(EXPECTED_STATE_KEYS.difference(state_keys))
        if missing_state_keys:
            raise AssertionError(f"agent loop state keys missing {missing_state_keys}: {coverage}")
        if coverage.get("stateKeyCount") != len(coverage.get("stateKeys") or []):
            raise AssertionError(f"agent loop state key count mismatch: {coverage}")
        if coverage.get("stateKeyParity") is not True:
            raise AssertionError(f"agent loop state key parity mismatch: {coverage}")
        if coverage.get("loopPhases") != EXPECTED_LOOP_PHASES:
            raise AssertionError(f"agent loop phase list mismatch: {coverage}")
        if coverage.get("loopPhaseCount") != len(EXPECTED_LOOP_PHASES):
            raise AssertionError(f"agent loop phase count mismatch: {coverage}")
        if coverage.get("loopPhaseParity") is not True:
            raise AssertionError(f"agent loop phase parity mismatch: {coverage}")
        if coverage.get("loopPhaseProofs") != EXPECTED_PHASE_PROOFS:
            raise AssertionError(f"agent loop phase proof map mismatch: {coverage}")
        if coverage.get("loopPhaseProofCount") != len(EXPECTED_PHASE_PROOFS):
            raise AssertionError(f"agent loop phase proof count mismatch: {coverage}")
        if coverage.get("loopPhaseProofParity") is not True:
            raise AssertionError(f"agent loop phase proof parity mismatch: {coverage}")
        for phase, proof_names in EXPECTED_PHASE_PROOFS.items():
            missing_phase_files = sorted(name for name in proof_names if not (ROOT / "scripts" / name).is_file())
            if missing_phase_files:
                raise AssertionError(f"agent loop phase {phase} names missing proof files {missing_phase_files}: {coverage}")
        if coverage.get("loopPhaseProofFileParity") is not True:
            raise AssertionError(f"agent loop phase proof-file parity mismatch: {coverage}")
        visual_state_keys = set(coverage.get("visualStateKeys") or [])
        for key in ("agents", "agentActions", "displayChatService", "displayResultsStore", "displayActivityFeed"):
            if key not in visual_state_keys:
                raise AssertionError(f"agent loop visual state key missing {key}: {coverage}")
        if coverage.get("visualStateKeyParity") is not True:
            raise AssertionError(f"agent loop visual state key parity mismatch: {coverage}")

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
