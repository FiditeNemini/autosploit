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

REQUIRED_ENDPOINTS = {
    "/state",
    "/messages",
    "/results",
    "/qa/tool-coverage",
    "/qa/subtab-coverage",
    "/qa/agent-loop-coverage",
    "/qa/tool-flow-coverage",
    "/qa/runtime-coverage",
    "/qa/context-coverage",
    "/qa/settings-coverage",
    "/qa/visual-coverage",
    "/qa/session-coverage",
    "/qa/tab-action-coverage",
    "/qa/chat-coverage",
    "/qa/result-parser-coverage",
    "/qa/tool-family-fanout-coverage",
    "/qa/proof-ledger",
    "/qa/artifact-ledger",
    "/qa/checkpoint-ledger",
    "/qa/audit-ledger",
    "/qa/gap-ledger",
}

REQUIRED_PROOFS = {
    "app-qa-matrix-smoke-proof.py",
    "tool-registry-coverage-proof.py",
    "subtab-coverage-proof.py",
    "agent-loop-coverage-proof.py",
    "tool-flow-coverage-proof.py",
    "runtime-coverage-proof.py",
    "context-coverage-proof.py",
    "settings-coverage-proof.py",
    "visual-coverage-proof.py",
    "session-coverage-proof.py",
    "tab-action-coverage-proof.py",
    "chat-coverage-proof.py",
    "result-parser-routing-proof.py",
    "tool-family-fanout-coverage-proof.py",
    "proof-ledger-proof.py",
    "artifact-ledger-proof.py",
    "checkpoint-ledger-proof.py",
    "audit-ledger-proof.py",
    "gap-ledger-proof.py",
}

REQUIRED_GROUPS = {
    "appState",
    "chatAndContext",
    "runtimeAndCache",
    "settingsAndVisuals",
    "toolsAndParsers",
    "tabsAndSessions",
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


def assert_coverage_index() -> None:
    state = request("GET", "/state")
    index = request("GET", "/qa/coverage-index")
    proof = request("GET", "/qa/proof-ledger")
    checkpoint = request("GET", "/qa/checkpoint-ledger")
    audit = request("GET", "/qa/audit-ledger")
    gap = request("GET", "/qa/gap-ledger")

    if index.get("ok") is not True:
        raise AssertionError(f"/qa/coverage-index failed: {index}")
    if index.get("endpointCount", 0) < len(REQUIRED_ENDPOINTS):
        raise AssertionError(f"coverage index endpoint count mismatch: {index}")
    if index.get("proofCount", 0) < len(REQUIRED_PROOFS):
        raise AssertionError(f"coverage index proof count mismatch: {index}")

    endpoints = set(index.get("endpoints") or [])
    missing_endpoints = sorted(REQUIRED_ENDPOINTS.difference(endpoints))
    if missing_endpoints:
        raise AssertionError(f"coverage index missing endpoints {missing_endpoints}: {index}")

    proofs = set(index.get("proofs") or [])
    missing_proofs = sorted(REQUIRED_PROOFS.difference(proofs))
    if missing_proofs:
        raise AssertionError(f"coverage index missing proofs {missing_proofs}: {index}")
    missing_files = sorted(name for name in REQUIRED_PROOFS if not (ROOT / "scripts" / name).is_file())
    if missing_files:
        raise AssertionError(f"coverage index names non-existent proof files: {missing_files}")

    groups = index.get("groups") or {}
    missing_groups = sorted(name for name in REQUIRED_GROUPS if name not in groups)
    if missing_groups:
        raise AssertionError(f"coverage index missing groups {missing_groups}: {index}")
    for name, group in groups.items():
        endpoints_for_group = group.get("endpoints") or []
        proofs_for_group = group.get("proofs") or []
        if not endpoints_for_group:
            raise AssertionError(f"coverage index group has no endpoints {name}: {group}")
        if not proofs_for_group:
            raise AssertionError(f"coverage index group has no proofs {name}: {group}")
        if group.get("endpointCount") != len(endpoints_for_group):
            raise AssertionError(f"coverage index group endpoint count mismatch {name}: {group}")
        if group.get("proofCount") != len(proofs_for_group):
            raise AssertionError(f"coverage index group proof count mismatch {name}: {group}")
    app_state_group = groups.get("appState") or {}
    if app_state_group.get("stateRouteCount", 0) < 14:
        raise AssertionError(f"coverage index app state route count mismatch: {app_state_group}")
    if app_state_group.get("subtabStateTabCount", 0) < 8:
        raise AssertionError(f"coverage index app state subtab count mismatch: {app_state_group}")
    if app_state_group.get("subtabStateProofCount", 0) < 8:
        raise AssertionError(f"coverage index app state subtab proof count mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCount", 0) < 120:
        raise AssertionError(f"coverage index app state proof ledger count mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCategoryCounts") != proof.get("categoryCounts"):
        raise AssertionError(f"coverage index app state proof ledger category counts mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCategorySurfaces") != proof.get("categorySurfaces"):
        raise AssertionError(f"coverage index app state proof ledger category surfaces mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCategorySurfaceCount") != proof.get("categorySurfaceCount"):
        raise AssertionError(f"coverage index app state proof ledger category surface count mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCategoryOtherCount") != proof.get("categoryOtherCount"):
        raise AssertionError(f"coverage index app state proof ledger category other count mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCategoryTotalCount") != proof.get("categoryTotalCount"):
        raise AssertionError(f"coverage index app state proof ledger category total count mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCategoryParity") != proof.get("categoryParity"):
        raise AssertionError(f"coverage index app state proof ledger category parity mismatch: {app_state_group}")
    expected_categories = {
        name: category.get("count")
        for name, category in (proof.get("categories") or {}).items()
        if name in {"agent", "chat", "context", "runtime", "settings", "tabs", "tools", "visual"}
    }
    if app_state_group.get("proofCategoryCounts") != expected_categories:
        raise AssertionError(f"coverage index app state proof category counts mismatch: {app_state_group}")
    if app_state_group.get("proofCategorySurfaces") != sorted(expected_categories):
        raise AssertionError(f"coverage index app state proof category surfaces mismatch: {app_state_group}")
    if app_state_group.get("proofCategorySurfaceCount") != len(expected_categories):
        raise AssertionError(f"coverage index app state proof category surface count mismatch: {app_state_group}")
    expected_category_total = sum(
        category.get("count", 0)
        for category in (proof.get("categories") or {}).values()
    )
    if app_state_group.get("proofCategoryTotalCount") != expected_category_total:
        raise AssertionError(f"coverage index app state proof category total mismatch: {app_state_group}")
    if app_state_group.get("proofCategoryTotalCount") != proof.get("proofCount"):
        raise AssertionError(f"coverage index app state proof category total does not match proof ledger: {app_state_group}")
    if app_state_group.get("proofCategoryParity") is not True:
        raise AssertionError(f"coverage index app state proof category parity flag mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerVisualManifestCount", 0) < 22:
        raise AssertionError(f"coverage index app state artifact visual count mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerLiveProofCount", 0) < 18:
        raise AssertionError(f"coverage index app state artifact live count mismatch: {app_state_group}")
    if app_state_group.get("missingVisualCaptureCount", 1) != 0:
        raise AssertionError(f"coverage index app state missing visual captures: {app_state_group}")
    if app_state_group.get("checkpointLedgerCount", 0) < 200:
        raise AssertionError(f"coverage index app state checkpoint ledger count mismatch: {app_state_group}")
    if app_state_group.get("completeCheckpointCount") != checkpoint.get("completeCheckpointCount"):
        raise AssertionError(f"coverage index app state complete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("incompleteCheckpointCount") != len(checkpoint.get("incompleteCheckpoints") or []):
        raise AssertionError(f"coverage index app state incomplete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("checkpointCompletionRatio") != checkpoint.get("checkpointCompletionRatio"):
        raise AssertionError(f"coverage index app state checkpoint ratio mismatch: {app_state_group}")
    if app_state_group.get("latestCheckpoint") != checkpoint.get("latestCheckpoint"):
        raise AssertionError(f"coverage index app state latest checkpoint mismatch: {app_state_group}")
    if app_state_group.get("latestCheckpointNumber") != checkpoint.get("latestCheckpointNumber"):
        raise AssertionError(f"coverage index app state latest checkpoint number mismatch: {app_state_group}")
    if app_state_group.get("auditLedgerCount", 0) < 300:
        raise AssertionError(f"coverage index app state audit ledger count mismatch: {app_state_group}")
    if app_state_group.get("auditProofCategoryCounts") != audit.get("proofCategoryCounts"):
        raise AssertionError(f"coverage index app state audit proof category counts mismatch: {app_state_group}")
    if app_state_group.get("auditProofCategorySurfaces") != audit.get("proofCategorySurfaces"):
        raise AssertionError(f"coverage index app state audit proof surfaces mismatch: {app_state_group}")
    if app_state_group.get("auditProofCategorySurfaceCount") != audit.get("proofCategorySurfaceCount"):
        raise AssertionError(f"coverage index app state audit proof surface count mismatch: {app_state_group}")
    if app_state_group.get("auditProofLedgerCategoryOtherCount") != audit.get("proofLedgerCategoryOtherCount"):
        raise AssertionError(f"coverage index app state audit source proof other count mismatch: {app_state_group}")
    if app_state_group.get("auditProofCategoryTotalCount") != audit.get("proofCategoryTotalCount"):
        raise AssertionError(f"coverage index app state audit proof total count mismatch: {app_state_group}")
    if app_state_group.get("auditProofCategoryParity") != audit.get("proofCategoryParity"):
        raise AssertionError(f"coverage index app state audit proof parity mismatch: {app_state_group}")
    if app_state_group.get("currentGapCount", -1) != 1:
        raise AssertionError(f"coverage index app state current gap count mismatch: {app_state_group}")
    if app_state_group.get("openGapIds") != gap.get("openGapIds"):
        raise AssertionError(f"coverage index app state open gap ids mismatch: {app_state_group}")
    if app_state_group.get("gapContractCount") != len(gap.get("gapContracts") or {}):
        raise AssertionError(f"coverage index app state gap contract count mismatch: {app_state_group}")
    if "qwenMultimodalRuntime" not in (app_state_group.get("openGapIds") or []):
        raise AssertionError(f"coverage index app state missing qwen multimodal gap id: {app_state_group}")
    runtime_group = groups.get("runtimeAndCache") or {}
    if runtime_group.get("liveProofArtifactCount", 0) < 6:
        raise AssertionError(f"coverage index runtime live artifact count mismatch: {runtime_group}")
    if set(runtime_group.get("supportedFamilies") or []) != {"qwen", "minimax"}:
        raise AssertionError(f"coverage index runtime supported family mismatch: {runtime_group}")
    if runtime_group.get("cacheResponseMethod") != "prefix-cache-l2-turboquant":
        raise AssertionError(f"coverage index runtime cache response method mismatch: {runtime_group}")
    runtime_coverage = request("GET", "/qa/runtime-coverage")
    if runtime_group.get("cacheResponsesInferenceMethod") != runtime_coverage.get("cacheResponsesInferenceMethod"):
        raise AssertionError(f"coverage index runtime cache responses inference method mismatch: {runtime_group}")
    if runtime_group.get("newModelSessionBehavior") != runtime_coverage.get("newModelSessionBehavior"):
        raise AssertionError(f"coverage index runtime new model session behavior mismatch: {runtime_group}")
    if runtime_group.get("cacheComponents") != runtime_coverage.get("cacheComponents"):
        raise AssertionError(f"coverage index runtime cache components mismatch: {runtime_group}")
    if runtime_group.get("cacheComponentCount") != runtime_coverage.get("cacheComponentCount"):
        raise AssertionError(f"coverage index runtime cache component count mismatch: {runtime_group}")
    if runtime_group.get("cacheComponentParity") != runtime_coverage.get("cacheComponentParity"):
        raise AssertionError(f"coverage index runtime cache component parity mismatch: {runtime_group}")
    chat_context_group = groups.get("chatAndContext") or {}
    chat_coverage = request("GET", "/qa/chat-coverage")
    if chat_context_group.get("stateKeyCount", 0) < 19:
        raise AssertionError(f"coverage index chat/context state key count mismatch: {chat_context_group}")
    if chat_context_group.get("headerCacheBadges") != chat_coverage.get("headerCacheBadges"):
        raise AssertionError(f"coverage index chat/context header cache badges mismatch: {chat_context_group}")
    if chat_context_group.get("headerCacheBadgeCount") != chat_coverage.get("headerCacheBadgeCount"):
        raise AssertionError(f"coverage index chat/context header cache badge count mismatch: {chat_context_group}")
    if chat_context_group.get("headerCacheBadgeParity") != chat_coverage.get("headerCacheBadgeParity"):
        raise AssertionError(f"coverage index chat/context header cache badge parity mismatch: {chat_context_group}")
    if chat_context_group.get("cacheSessionIndicator") != chat_coverage.get("cacheSessionIndicator"):
        raise AssertionError(f"coverage index chat/context cache session indicator mismatch: {chat_context_group}")
    if chat_context_group.get("cacheResponsesInferenceMethod") != chat_coverage.get("cacheResponsesInferenceMethod"):
        raise AssertionError(f"coverage index chat/context cache responses inference method mismatch: {chat_context_group}")
    if chat_context_group.get("newModelSessionBehavior") != chat_coverage.get("newModelSessionBehavior"):
        raise AssertionError(f"coverage index chat/context new model session behavior mismatch: {chat_context_group}")
    if chat_context_group.get("newContextSessionBoundary") != chat_coverage.get("newContextSessionBoundary"):
        raise AssertionError(f"coverage index chat/context new context boundary mismatch: {chat_context_group}")
    if chat_context_group.get("cacheSessionFields") != chat_coverage.get("cacheSessionFields"):
        raise AssertionError(f"coverage index chat/context cache session fields mismatch: {chat_context_group}")
    if chat_context_group.get("cacheSessionFieldCount") != chat_coverage.get("cacheSessionFieldCount"):
        raise AssertionError(f"coverage index chat/context cache session field count mismatch: {chat_context_group}")
    if chat_context_group.get("cacheSessionFieldParity") != chat_coverage.get("cacheSessionFieldParity"):
        raise AssertionError(f"coverage index chat/context cache session field parity mismatch: {chat_context_group}")
    context_coverage = request("GET", "/qa/context-coverage")
    if chat_context_group.get("retrievalSources") != context_coverage.get("retrievalSources"):
        raise AssertionError(f"coverage index chat/context retrieval sources mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSourceCount") != context_coverage.get("retrievalSourceCount"):
        raise AssertionError(f"coverage index chat/context retrieval source count mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSourceParity") != context_coverage.get("retrievalSourceParity"):
        raise AssertionError(f"coverage index chat/context retrieval source parity mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModes") != context_coverage.get("contextDeliveryModes"):
        raise AssertionError(f"coverage index chat/context delivery modes mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModeCount") != context_coverage.get("contextDeliveryModeCount"):
        raise AssertionError(f"coverage index chat/context delivery mode count mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModeParity") != context_coverage.get("contextDeliveryModeParity"):
        raise AssertionError(f"coverage index chat/context delivery mode parity mismatch: {chat_context_group}")
    settings_visuals_group = groups.get("settingsAndVisuals") or {}
    if settings_visuals_group.get("settingsVisualManifestCount", 0) < 6:
        raise AssertionError(f"coverage index settings visual manifest count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualManifestCount", 0) < 22:
        raise AssertionError(f"coverage index visual manifest count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("actualCaptureCount", 0) < 48:
        raise AssertionError(f"coverage index visual capture count mismatch: {settings_visuals_group}")
    tools_parsers_group = groups.get("toolsAndParsers") or {}
    if tools_parsers_group.get("toolCount", 0) < 38:
        raise AssertionError(f"coverage index tools/parsers tool count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("callbackCount", 0) < 3:
        raise AssertionError(f"coverage index tools/parsers callback count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("familyFanoutCount", 0) < 7:
        raise AssertionError(f"coverage index tools/parsers family fanout count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("stateKeyCount", 0) < 5:
        raise AssertionError(f"coverage index tools/parsers state key count mismatch: {tools_parsers_group}")
    tool_flow = request("GET", "/qa/tool-flow-coverage")
    if tools_parsers_group.get("toolSchemaCap") != tool_flow.get("toolSchemaCap"):
        raise AssertionError(f"coverage index tools/parsers schema cap mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolSchemaPolicy") != tool_flow.get("toolSchemaPolicy"):
        raise AssertionError(f"coverage index tools/parsers schema policy mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolCatalogRoute") != tool_flow.get("toolCatalogRoute"):
        raise AssertionError(f"coverage index tools/parsers catalog route mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("structuredResultModeCount") != tool_flow.get("structuredResultModeCount"):
        raise AssertionError(f"coverage index tools/parsers structured result mode count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("rawResultModeCount") != tool_flow.get("rawResultModeCount"):
        raise AssertionError(f"coverage index tools/parsers raw result mode count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultModeCountParity") != tool_flow.get("resultModeCountParity"):
        raise AssertionError(f"coverage index tools/parsers result mode parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityStatuses") != tool_flow.get("tabActivityStatuses"):
        raise AssertionError(f"coverage index tools/parsers tab activity statuses mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityStatusCount") != tool_flow.get("tabActivityStatusCount"):
        raise AssertionError(f"coverage index tools/parsers tab activity status count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityStatusParity") != tool_flow.get("tabActivityStatusParity"):
        raise AssertionError(f"coverage index tools/parsers tab activity status parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityIndicatorContract") != tool_flow.get("tabActivityIndicatorContract"):
        raise AssertionError(f"coverage index tools/parsers tab activity indicator contract mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaces") != tool_flow.get("toolVisualSurfaces"):
        raise AssertionError(f"coverage index tools/parsers visual surfaces mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaceCount") != tool_flow.get("toolVisualSurfaceCount"):
        raise AssertionError(f"coverage index tools/parsers visual surface count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaceParity") != tool_flow.get("toolVisualSurfaceParity"):
        raise AssertionError(f"coverage index tools/parsers visual surface parity mismatch: {tools_parsers_group}")
    tabs_sessions_group = groups.get("tabsAndSessions") or {}
    if tabs_sessions_group.get("interactionModeCount", 0) < 3:
        raise AssertionError(f"coverage index tabs/sessions mode count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("coveredTabCount", 0) < 9:
        raise AssertionError(f"coverage index tabs/sessions tab count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("stateKeyCount", 0) < 12:
        raise AssertionError(f"coverage index tabs/sessions state key count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("actionStateKeyCount", 0) < 26:
        raise AssertionError(f"coverage index tabs/sessions action state key count mismatch: {tabs_sessions_group}")
    agent_loop = request("GET", "/qa/agent-loop-coverage")
    if tabs_sessions_group.get("agentLoopStateKeyCount") != agent_loop.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop state key count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopVisualStateKeys") != agent_loop.get("visualStateKeys"):
        raise AssertionError(f"coverage index tabs/sessions agent loop visual state keys mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatuses") != tool_flow.get("tabActivityStatuses"):
        raise AssertionError(f"coverage index tabs/sessions tab activity statuses mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatusCount") != tool_flow.get("tabActivityStatusCount"):
        raise AssertionError(f"coverage index tabs/sessions tab activity status count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatusParity") != tool_flow.get("tabActivityStatusParity"):
        raise AssertionError(f"coverage index tabs/sessions tab activity status parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityIndicatorContract") != tool_flow.get("tabActivityIndicatorContract"):
        raise AssertionError(f"coverage index tabs/sessions tab activity indicator contract mismatch: {tabs_sessions_group}")

    qa = state.get("qaCoverage") or {}
    if "/qa/coverage-index" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing coverage-index route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_coverage_index()
        print("coverage-index proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"coverage-index proof failed: {exc}", flush=True)
        raise SystemExit(1)
