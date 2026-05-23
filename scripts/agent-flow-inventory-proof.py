#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
SOURCE_ROOT = ROOT / "ExploitBot" / "Sources" / "ExploitBot"

EXPECTED_FILES = [
    "ExploitBot/Sources/ExploitBot/Services/ChatService.swift",
    "ExploitBot/Sources/ExploitBot/Services/AgentManager.swift",
    "ExploitBot/Sources/ExploitBot/Services/ToolDefinitions.swift",
    "ExploitBot/Sources/ExploitBot/Services/ToolExecutor.swift",
    "ExploitBot/Sources/ExploitBot/Services/ResultsStore.swift",
    "ExploitBot/Sources/ExploitBot/Services/ContextCatalogService.swift",
    "ExploitBot/Sources/ExploitBot/Services/ActivityFeed.swift",
    "ExploitBot/Sources/ExploitBot/Models/AppState.swift",
]

EXPECTED_GROUPS = [
    "conversationLoop",
    "agentManager",
    "toolCatalogue",
    "toolExecution",
    "resultIngestion",
    "contextCatalogue",
    "activityTelemetry",
    "appStateWiring",
]

EXPECTED_PHASES = [
    "sendGuard",
    "contextCatalogue",
    "toolSchemaRanking",
    "streamCompletion",
    "reasoningAndMetrics",
    "toolCallAccumulation",
    "manualSuggestion",
    "copilotApproval",
    "scopeEnforcement",
    "builtinCallbackExecution",
    "subprocessExecution",
    "resultIngestion",
    "activityTelemetry",
    "phaseAdvance",
    "loopContinuation",
    "stopCancel",
]

PHASE_TOKENS = {
    "sendGuard": ["guard !isWorking else", "isWorking = true"],
    "contextCatalogue": ["onContextUpdate", "buildContextSummary", "lastContextSelections"],
    "toolSchemaRanking": ["ToolDefinitions.forModel", "lastToolSchemaNames"],
    "streamCompletion": ["streamCompletion()", "session.bytes(for:"],
    "reasoningAndMetrics": ["reasoning_content", "stream_options", "cachedTokenCount"],
    "toolCallAccumulation": ["accumulatedToolCalls", "tool_calls", "ToolCall("],
    "manualSuggestion": ["interactionMode == .manual", "suggested"],
    "copilotApproval": ["interactionMode == .copilot", "PendingApproval", "approveToolCall"],
    "scopeEnforcement": ["ScopeChecker.extractTarget", "ScopeChecker.isInScope", "outside Op scope"],
    "builtinCallbackExecution": ["onSearchCVE", "onLookupCVE", "onSearchContext"],
    "subprocessExecution": ["toolExecutor.execute", "Process()", "buildEnvironment"],
    "resultIngestion": ["onToolResult", "resultsStore.ingest", "func ingest"],
    "activityTelemetry": ["onToolStart", "onToolComplete", "ActivityFeed"],
    "phaseAdvance": ["onPhaseComplete", "SCAN COMPLETE", "DETECT COMPLETE"],
    "loopContinuation": ["while iterations < maxIterations", "iterations += 1"],
    "stopCancel": ["streamSession?.invalidateAndCancel", "toolExecutor.cancel", "onToolCancel"],
}

EXPECTED_PROOFS = [
    "agent-flow-inventory-proof.py",
    "agent-loop-coverage-proof.py",
    "agent-tool-authorization-proof.py",
    "tool-flow-coverage-proof.py",
    "context-coverage-proof.py",
    "app-qa-matrix-smoke-proof.py",
]


def group_for(rel: str) -> str:
    name = Path(rel).name
    return {
        "ChatService.swift": "conversationLoop",
        "AgentManager.swift": "agentManager",
        "ToolDefinitions.swift": "toolCatalogue",
        "ToolExecutor.swift": "toolExecution",
        "ResultsStore.swift": "resultIngestion",
        "ContextCatalogService.swift": "contextCatalogue",
        "ActivityFeed.swift": "activityTelemetry",
        "AppState.swift": "appStateWiring",
    }[name]


def proof_for(group: str) -> str:
    return {
        "conversationLoop": "agent-loop-coverage-proof.py",
        "agentManager": "agent-loop-coverage-proof.py",
        "toolCatalogue": "tool-flow-coverage-proof.py",
        "toolExecution": "tool-flow-coverage-proof.py",
        "resultIngestion": "tool-flow-coverage-proof.py",
        "contextCatalogue": "context-coverage-proof.py",
        "activityTelemetry": "app-qa-matrix-smoke-proof.py",
        "appStateWiring": "agent-tool-authorization-proof.py",
    }[group]


def parse_file(rel: str) -> dict[str, object]:
    path = ROOT / rel
    source = path.read_text(encoding="utf-8")
    group = group_for(rel)
    types = [
        {"kind": kind, "name": name}
        for kind, name in re.findall(r"^\s*(struct|class|enum|protocol)\s+([A-Za-z_][A-Za-z0-9_]*)", source, flags=re.MULTILINE)
    ]
    functions = re.findall(
        r"^\s*(?:private\s+|static\s+|@MainActor\s+|mutating\s+|nonisolated\s+|override\s+|class\s+|final\s+|@discardableResult\s+)*func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        source,
        flags=re.MULTILINE,
    )
    callbacks = sorted(set(re.findall(r"\b(on[A-Z][A-Za-z0-9_]*)\b", source)))
    return {
        "file": rel,
        "group": group,
        "proofOwner": proof_for(group),
        "types": types,
        "typeCount": len(types),
        "functions": functions,
        "functionCount": len(functions),
        "callbacks": callbacks,
        "callbackCount": len(callbacks),
    }


def source_inventory() -> list[dict[str, object]]:
    return [parse_file(rel) for rel in EXPECTED_FILES]


def phase_coverage() -> dict[str, dict[str, object]]:
    corpus_by_file = {rel: (ROOT / rel).read_text(encoding="utf-8") for rel in EXPECTED_FILES}
    result: dict[str, dict[str, object]] = {}
    for phase, tokens in PHASE_TOKENS.items():
        files = [
            rel
            for rel, source in corpus_by_file.items()
            if any(token in source for token in tokens)
        ]
        result[phase] = {
            "tokens": tokens,
            "files": files,
            "fileCount": len(files),
            "covered": bool(files),
        }
    return result


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

        inventory = source_inventory()
        phases = phase_coverage()
        payload = request("GET", "/qa/agent-flow-inventory")
        if payload.get("ok") is not True:
            raise AssertionError(f"agent flow inventory route failed: {payload}")
        if payload.get("sourceRoot") != "ExploitBot/Sources/ExploitBot":
            raise AssertionError(f"agent flow inventory source root mismatch: {payload}")
        if payload.get("files") != inventory:
            raise AssertionError(f"agent flow inventory file list mismatch: {payload}")
        if payload.get("fileCount") != len(inventory):
            raise AssertionError(f"agent flow inventory file count mismatch: {payload}")
        if payload.get("typeCount") != sum(item["typeCount"] for item in inventory):
            raise AssertionError(f"agent flow inventory type count mismatch: {payload}")
        if payload.get("functionCount") != sum(item["functionCount"] for item in inventory):
            raise AssertionError(f"agent flow inventory function count mismatch: {payload}")
        if payload.get("callbackCount") != sum(item["callbackCount"] for item in inventory):
            raise AssertionError(f"agent flow inventory callback count mismatch: {payload}")

        if payload.get("groups") != EXPECTED_GROUPS:
            raise AssertionError(f"agent flow inventory groups mismatch: {payload}")
        expected_counts = dict(Counter(item["group"] for item in inventory))
        expected_counts = {group: expected_counts.get(group, 0) for group in EXPECTED_GROUPS}
        if payload.get("groupCounts") != expected_counts:
            raise AssertionError(f"agent flow inventory group counts mismatch: {payload}")

        if payload.get("flowPhases") != EXPECTED_PHASES:
            raise AssertionError(f"agent flow inventory phase list mismatch: {payload}")
        if payload.get("phaseCoverage") != phases:
            raise AssertionError(f"agent flow inventory phase coverage mismatch: {payload}")
        if payload.get("phaseCoverageParity") is not True:
            raise AssertionError(f"agent flow inventory phase coverage parity mismatch: {payload}")

        state = request("GET", "/state")
        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/agent-flow-inventory" not in state_routes:
            raise AssertionError(f"state route list missing agent flow inventory route: {state_routes}")

        index = request("GET", "/qa/coverage-index")
        group = (index.get("groups") or {}).get("chatAndContext") or {}
        if group.get("agentFlowInventoryFileCount") != payload.get("fileCount"):
            raise AssertionError(f"coverage index agent flow file count mismatch: {index}")
        if group.get("agentFlowInventoryFunctionCount") != payload.get("functionCount"):
            raise AssertionError(f"coverage index agent flow function count mismatch: {index}")
        if group.get("agentFlowInventoryGroupCounts") != payload.get("groupCounts"):
            raise AssertionError(f"coverage index agent flow group counts mismatch: {index}")
        if group.get("agentFlowInventoryPhaseCoverageParity") != payload.get("phaseCoverageParity"):
            raise AssertionError(f"coverage index agent flow phase parity mismatch: {index}")
        if group.get("agentFlowInventoryProofFileParity") != payload.get("proofFileParity"):
            raise AssertionError(f"coverage index agent flow proof parity mismatch: {index}")

        proofs = payload.get("proofs") or []
        if proofs != EXPECTED_PROOFS:
            raise AssertionError(f"agent flow inventory proof list mismatch: {payload}")
        if payload.get("proofCount") != len(EXPECTED_PROOFS):
            raise AssertionError(f"agent flow inventory proof count mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"agent flow inventory proof-file parity mismatch: {payload}")

        print("agent-flow-inventory proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"agent-flow-inventory proof failed: {exc}", flush=True)
        raise SystemExit(1)
