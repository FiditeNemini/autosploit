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
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"


REMOVED_PROFILE_PATTERNS = (
    r"\bModelProfile\b",
    r"\bmodelProfile\b",
    r"\bmaxToolCount\b",
    r"\bmodelProfileHint\b",
    r"\bcuratedModels\b",
)

REQUIRED_CONTEXT_HOOKS = (
    "onContextUpdate",
    "search_context",
    "lastContextSummary",
    "lastToolSchemaNames",
    "context.catalog.maxSnippets",
)

REQUIRED_SUBTAB_PROOFS = (
    "recon-subtab-state-proof.py",
    "web-subtab-state-proof.py",
    "network-subtab-state-proof.py",
    "creds-subtab-state-proof.py",
    "exploit-subtab-state-proof.py",
    "post-subtab-state-proof.py",
    "osint-subtab-state-proof.py",
    "report-subtab-state-proof.py",
)


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


def source_files() -> list[Path]:
    return sorted((ROOT / "ExploitBot" / "Sources" / "ExploitBot").rglob("*.swift"))


def assert_removed_profile_code() -> None:
    offenders: list[str] = []
    for path in source_files():
        text = path.read_text(encoding="utf-8")
        for pattern in REMOVED_PROFILE_PATTERNS:
            if re.search(pattern, text):
                offenders.append(f"{path.relative_to(ROOT)}:{pattern}")
    if offenders:
        raise AssertionError(f"removed model-profile code still present: {offenders}")


def assert_required_context_hooks() -> None:
    corpus = "\n".join(path.read_text(encoding="utf-8") for path in source_files())
    missing = [hook for hook in REQUIRED_CONTEXT_HOOKS if hook not in corpus]
    if missing:
        raise AssertionError(f"required context hooks missing: {missing}")


def assert_testserver_smoke() -> None:
    state = request("GET", "/state")
    messages = request("GET", "/messages")
    results = request("GET", "/results")
    subtab_coverage = request("GET", "/qa/subtab-coverage")
    agent_loop_coverage = request("GET", "/qa/agent-loop-coverage")
    tool_flow_coverage = request("GET", "/qa/tool-flow-coverage")
    runtime_coverage = request("GET", "/qa/runtime-coverage")
    context_coverage = request("GET", "/qa/context-coverage")
    settings_coverage = request("GET", "/qa/settings-coverage")
    visual_coverage = request("GET", "/qa/visual-coverage")
    session_coverage = request("GET", "/qa/session-coverage")
    tab_action_coverage = request("GET", "/qa/tab-action-coverage")
    chat_coverage = request("GET", "/qa/chat-coverage")
    coverage_index = request("GET", "/qa/coverage-index")
    proof_ledger = request("GET", "/qa/proof-ledger")
    artifact_ledger = request("GET", "/qa/artifact-ledger")
    checkpoint_ledger = request("GET", "/qa/checkpoint-ledger")
    audit_ledger = request("GET", "/qa/audit-ledger")
    gap_ledger = request("GET", "/qa/gap-ledger")

    required_state_keys = {
        "activeTab",
        "mode",
        "engineConfig",
        "contextCatalog",
        "requestContext",
        "agents",
        "toolSettings",
        "feedRecent",
    }
    missing = sorted(required_state_keys.difference(state))
    if missing:
        raise AssertionError(f"/state missing QA keys {missing}: {state}")
    if not isinstance(messages, list):
        raise AssertionError(f"/messages did not return a list: {messages}")
    for key in ("ports", "vulns", "osint", "postAttribution"):
        if key not in results or not isinstance(results[key], list):
            raise AssertionError(f"/results missing list key {key}: {results}")

    qa = state.get("qaCoverage") or {}
    if qa.get("staticProfilesRemoved") is not True:
        raise AssertionError(f"/state missing profile-removal QA coverage: {qa}")
    if qa.get("testServerSmoke") is not True:
        raise AssertionError(f"/state missing TestServer smoke QA coverage: {qa}")
    if sorted(qa.get("contextHooks") or []) != sorted(REQUIRED_CONTEXT_HOOKS):
        raise AssertionError(f"/state missing required context hook names: {qa}")
    if sorted(qa.get("subtabStateProofs") or []) != sorted(REQUIRED_SUBTAB_PROOFS):
        raise AssertionError(f"/state missing shared subtab-state proof coverage: {qa}")
    expected_subtab_tabs = ["creds", "exploit", "network", "osint", "post", "recon", "report", "web"]
    if sorted(qa.get("subtabStateTabs") or []) != expected_subtab_tabs:
        raise AssertionError(f"/state missing shared subtab-state tabs: {qa}")
    if "/qa/subtab-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing subtab coverage route contract: {qa}")
    if "/qa/agent-loop-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing agent loop coverage route contract: {qa}")
    if "/qa/tool-flow-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing tool flow coverage route contract: {qa}")
    if "/qa/runtime-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing runtime coverage route contract: {qa}")
    if "/qa/context-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing context coverage route contract: {qa}")
    if "/qa/settings-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing settings coverage route contract: {qa}")
    if "/qa/visual-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing visual coverage route contract: {qa}")
    if "/qa/session-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing session coverage route contract: {qa}")
    if "/qa/tab-action-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing tab action coverage route contract: {qa}")
    if "/qa/chat-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing chat coverage route contract: {qa}")
    if "/qa/coverage-index" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing coverage-index route contract: {qa}")
    if "/qa/proof-ledger" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing proof-ledger route contract: {qa}")
    if "/qa/artifact-ledger" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing artifact-ledger route contract: {qa}")
    if "/qa/checkpoint-ledger" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing checkpoint-ledger route contract: {qa}")
    if "/qa/audit-ledger" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing audit-ledger route contract: {qa}")
    if "/qa/gap-ledger" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing gap-ledger route contract: {qa}")
    if subtab_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/subtab-coverage failed: {subtab_coverage}")
    if sorted((subtab_coverage.get("tabs") or {}).keys()) != expected_subtab_tabs:
        raise AssertionError(f"/qa/subtab-coverage tabs mismatch: {subtab_coverage}")
    if agent_loop_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/agent-loop-coverage failed: {agent_loop_coverage}")
    if agent_loop_coverage.get("modes") != {"autopilot": "execute", "copilot": "approval", "manual": "suggest"}:
        raise AssertionError(f"/qa/agent-loop-coverage mode contract mismatch: {agent_loop_coverage}")
    if "taskSent" not in (agent_loop_coverage.get("actionTelemetryFields") or []):
        raise AssertionError(f"/qa/agent-loop-coverage telemetry fields mismatch: {agent_loop_coverage}")
    if agent_loop_coverage.get("stateKeyCount") != len(agent_loop_coverage.get("stateKeys") or []):
        raise AssertionError(f"/qa/agent-loop-coverage state key count mismatch: {agent_loop_coverage}")
    for key in ("agents", "agentActions", "displayChatService", "displayResultsStore", "displayActivityFeed"):
        if key not in (agent_loop_coverage.get("visualStateKeys") or []):
            raise AssertionError(f"/qa/agent-loop-coverage visual state key missing {key}: {agent_loop_coverage}")
    if tool_flow_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/tool-flow-coverage failed: {tool_flow_coverage}")
    if tool_flow_coverage.get("toolCount") != 38 or tool_flow_coverage.get("callbackCount") != 3:
        raise AssertionError(f"/qa/tool-flow-coverage registry counters mismatch: {tool_flow_coverage}")
    if tool_flow_coverage.get("toolSchemaCap") != 12:
        raise AssertionError(f"/qa/tool-flow-coverage schema cap mismatch: {tool_flow_coverage}")
    if tool_flow_coverage.get("toolSchemaPolicy") != "prompt-tab-ranked-installed-cap":
        raise AssertionError(f"/qa/tool-flow-coverage schema policy mismatch: {tool_flow_coverage}")
    if tool_flow_coverage.get("toolCatalogRoute") != "/qa/tool-catalog":
        raise AssertionError(f"/qa/tool-flow-coverage catalog route mismatch: {tool_flow_coverage}")
    if tool_flow_coverage.get("structuredResultModeCount", 0) < 29:
        raise AssertionError(f"/qa/tool-flow-coverage structured mode count mismatch: {tool_flow_coverage}")
    if tool_flow_coverage.get("rawResultModeCount", 0) < 9:
        raise AssertionError(f"/qa/tool-flow-coverage raw mode count mismatch: {tool_flow_coverage}")
    if tool_flow_coverage.get("resultModeCountParity") is not True:
        raise AssertionError(f"/qa/tool-flow-coverage result mode parity mismatch: {tool_flow_coverage}")
    if tool_flow_coverage.get("tabActivityStatuses") != ["running", "done", "failed", "canceled"]:
        raise AssertionError(f"/qa/tool-flow-coverage tab activity statuses mismatch: {tool_flow_coverage}")
    if tool_flow_coverage.get("tabActivityStatusCount") != 4:
        raise AssertionError(f"/qa/tool-flow-coverage tab activity status count mismatch: {tool_flow_coverage}")
    if tool_flow_coverage.get("tabActivityStatusParity") is not True:
        raise AssertionError(f"/qa/tool-flow-coverage tab activity status parity mismatch: {tool_flow_coverage}")
    if tool_flow_coverage.get("tabActivityIndicatorContract") != "status-dot-running-ring":
        raise AssertionError(f"/qa/tool-flow-coverage tab activity indicator contract mismatch: {tool_flow_coverage}")
    expected_tool_visual_surfaces = [
        "chatToolCard",
        "activityFeedStatus",
        "tabStatusIndicator",
        "parsedResultRow",
        "contextCatalogHit",
        "toolOutputExpansion",
    ]
    if tool_flow_coverage.get("toolVisualSurfaces") != expected_tool_visual_surfaces:
        raise AssertionError(f"/qa/tool-flow-coverage visual surfaces mismatch: {tool_flow_coverage}")
    if tool_flow_coverage.get("toolVisualSurfaceCount") != len(expected_tool_visual_surfaces):
        raise AssertionError(f"/qa/tool-flow-coverage visual surface count mismatch: {tool_flow_coverage}")
    if tool_flow_coverage.get("toolVisualSurfaceParity") is not True:
        raise AssertionError(f"/qa/tool-flow-coverage visual surface parity mismatch: {tool_flow_coverage}")
    if "messages.toolCards" not in (tool_flow_coverage.get("stateKeys") or []):
        raise AssertionError(f"/qa/tool-flow-coverage state key mismatch: {tool_flow_coverage}")
    if runtime_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/runtime-coverage failed: {runtime_coverage}")
    if runtime_coverage.get("cacheResponseMethod") != "prefix-cache-l2-turboquant":
        raise AssertionError(f"/qa/runtime-coverage cache method mismatch: {runtime_coverage}")
    expected_runtime_cache_components = [
        "prefixCache",
        "promptL2Disk",
        "pagedKVCache",
        "blockL2Disk",
        "turboQuantKV",
        "ssmCompanionL2",
        "newContextPreservesEngineSession",
    ]
    if runtime_coverage.get("cacheComponents") != expected_runtime_cache_components:
        raise AssertionError(f"/qa/runtime-coverage cache component list mismatch: {runtime_coverage}")
    if runtime_coverage.get("cacheComponentCount") != len(expected_runtime_cache_components):
        raise AssertionError(f"/qa/runtime-coverage cache component count mismatch: {runtime_coverage}")
    if runtime_coverage.get("cacheComponentParity") is not True:
        raise AssertionError(f"/qa/runtime-coverage cache component parity mismatch: {runtime_coverage}")
    if runtime_coverage.get("cacheComponentProofCount") != len(expected_runtime_cache_components):
        raise AssertionError(f"/qa/runtime-coverage cache component proof count mismatch: {runtime_coverage}")
    if runtime_coverage.get("cacheComponentProofParity") is not True:
        raise AssertionError(f"/qa/runtime-coverage cache component proof parity mismatch: {runtime_coverage}")
    if runtime_coverage.get("liveProofArtifactCount", 0) < 6:
        raise AssertionError(f"/qa/runtime-coverage live artifact count mismatch: {runtime_coverage}")
    if context_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/context-coverage failed: {context_coverage}")
    if context_coverage.get("searchToolName") != "search_context":
        raise AssertionError(f"/qa/context-coverage search tool mismatch: {context_coverage}")
    if context_coverage.get("automaticInjectedContextCap") != 4:
        raise AssertionError(f"/qa/context-coverage context cap mismatch: {context_coverage}")
    if not 1 <= context_coverage.get("currentInjectedContextLimit", 0) <= 4:
        raise AssertionError(f"/qa/context-coverage current context limit mismatch: {context_coverage}")
    expected_retrieval_sources = ["asset.port", "finding", "tool.output", "stash.note", "cve"]
    if context_coverage.get("retrievalSources") != expected_retrieval_sources:
        raise AssertionError(f"/qa/context-coverage retrieval source list mismatch: {context_coverage}")
    if context_coverage.get("retrievalSourceCount") != len(expected_retrieval_sources):
        raise AssertionError(f"/qa/context-coverage retrieval source count mismatch: {context_coverage}")
    if context_coverage.get("retrievalSourceParity") is not True:
        raise AssertionError(f"/qa/context-coverage retrieval source parity mismatch: {context_coverage}")
    expected_context_delivery_modes = [
        "automaticBoundedInjection",
        "onDemandSearchContext",
        "persistedTurnAudit",
        "durableEmbeddingIndex",
        "activeScopeStashRetrieval",
    ]
    if context_coverage.get("contextDeliveryModes") != expected_context_delivery_modes:
        raise AssertionError(f"/qa/context-coverage delivery modes mismatch: {context_coverage}")
    if context_coverage.get("contextDeliveryModeCount") != len(expected_context_delivery_modes):
        raise AssertionError(f"/qa/context-coverage delivery mode count mismatch: {context_coverage}")
    if context_coverage.get("contextDeliveryModeParity") is not True:
        raise AssertionError(f"/qa/context-coverage delivery mode parity mismatch: {context_coverage}")
    if "requestContext" not in (context_coverage.get("stateKeys") or []):
        raise AssertionError(f"/qa/context-coverage state key mismatch: {context_coverage}")
    if settings_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/settings-coverage failed: {settings_coverage}")
    if settings_coverage.get("categoryCount") != 9:
        raise AssertionError(f"/qa/settings-coverage category count mismatch: {settings_coverage}")
    if settings_coverage.get("cacheResponseMethod") != "prefix-cache-l2-turboquant":
        raise AssertionError(f"/qa/settings-coverage cache method mismatch: {settings_coverage}")
    if settings_coverage.get("visualManifestCount", 0) < 6:
        raise AssertionError(f"/qa/settings-coverage visual manifest count mismatch: {settings_coverage}")
    expected_settings_surfaces = [
        "engineModelRuntime",
        "contextAndCache",
        "agentControls",
        "cveDatabase",
        "toolInventory",
        "inferenceLogs",
        "visualStatusProofs",
    ]
    if settings_coverage.get("settingsSurfaces") != expected_settings_surfaces:
        raise AssertionError(f"/qa/settings-coverage surface list mismatch: {settings_coverage}")
    if settings_coverage.get("settingsSurfaceCount") != len(expected_settings_surfaces):
        raise AssertionError(f"/qa/settings-coverage surface count mismatch: {settings_coverage}")
    if settings_coverage.get("settingsSurfaceParity") is not True:
        raise AssertionError(f"/qa/settings-coverage surface parity mismatch: {settings_coverage}")
    if settings_coverage.get("settingsSurfaceProofCount") != len(expected_settings_surfaces):
        raise AssertionError(f"/qa/settings-coverage surface proof count mismatch: {settings_coverage}")
    if settings_coverage.get("settingsSurfaceProofParity") is not True:
        raise AssertionError(f"/qa/settings-coverage surface proof parity mismatch: {settings_coverage}")
    if visual_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/visual-coverage failed: {visual_coverage}")
    if visual_coverage.get("manifestCount", 0) < 22:
        raise AssertionError(f"/qa/visual-coverage manifest count mismatch: {visual_coverage}")
    if visual_coverage.get("minimumCaptureCount", 0) < 30:
        raise AssertionError(f"/qa/visual-coverage capture count mismatch: {visual_coverage}")
    if visual_coverage.get("actualCaptureCount", 0) < 48:
        raise AssertionError(f"/qa/visual-coverage actual capture count mismatch: {visual_coverage}")
    expected_visual_surfaces = [
        "chatAndScroll",
        "settingsAndCache",
        "contextInspectorAndAudit",
        "tabAndSubtabActivity",
        "osintScreenshots",
        "reportAndStash",
        "unsupportedAndPost",
        "toolActionPanels",
        "cveAndToolSettings",
    ]
    if visual_coverage.get("visualSurfaces") != expected_visual_surfaces:
        raise AssertionError(f"/qa/visual-coverage surface list mismatch: {visual_coverage}")
    if visual_coverage.get("visualSurfaceCount") != len(expected_visual_surfaces):
        raise AssertionError(f"/qa/visual-coverage surface count mismatch: {visual_coverage}")
    if visual_coverage.get("visualSurfaceParity") is not True:
        raise AssertionError(f"/qa/visual-coverage surface parity mismatch: {visual_coverage}")
    if visual_coverage.get("visualSurfaceProofCount") != len(expected_visual_surfaces):
        raise AssertionError(f"/qa/visual-coverage surface proof count mismatch: {visual_coverage}")
    if visual_coverage.get("visualSurfaceProofParity") is not True:
        raise AssertionError(f"/qa/visual-coverage surface proof parity mismatch: {visual_coverage}")
    if session_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/session-coverage failed: {session_coverage}")
    if session_coverage.get("interactionModes") != ["autopilot", "copilot", "manual"]:
        raise AssertionError(f"/qa/session-coverage mode order mismatch: {session_coverage}")
    if session_coverage.get("sidebarActions") != ["createOp", "renameOp", "switchOp", "deleteOp"]:
        raise AssertionError(f"/qa/session-coverage sidebar action mismatch: {session_coverage}")
    expected_session_workflow_surfaces = [
        "onboardingModeSelection",
        "sidebarOperationLifecycle",
        "windowOverlayControls",
        "modelFolderSelection",
        "persistenceAndResultRebuild",
        "findingWizardSubmit",
        "tabAndPhaseNavigation",
        "activityFeedControls",
    ]
    if session_coverage.get("sessionWorkflowSurfaces") != expected_session_workflow_surfaces:
        raise AssertionError(f"/qa/session-coverage workflow surfaces mismatch: {session_coverage}")
    if session_coverage.get("sessionWorkflowSurfaceCount") != len(expected_session_workflow_surfaces):
        raise AssertionError(f"/qa/session-coverage workflow surface count mismatch: {session_coverage}")
    if session_coverage.get("sessionWorkflowSurfaceParity") is not True:
        raise AssertionError(f"/qa/session-coverage workflow surface parity mismatch: {session_coverage}")
    if session_coverage.get("sessionWorkflowSurfaceProofCount") != len(expected_session_workflow_surfaces):
        raise AssertionError(f"/qa/session-coverage workflow surface proof count mismatch: {session_coverage}")
    if session_coverage.get("sessionWorkflowSurfaceProofParity") is not True:
        raise AssertionError(f"/qa/session-coverage workflow surface proof parity mismatch: {session_coverage}")
    if "modeSelection" not in (session_coverage.get("stateKeys") or []):
        raise AssertionError(f"/qa/session-coverage state key mismatch: {session_coverage}")
    if tab_action_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/tab-action-coverage failed: {tab_action_coverage}")
    if tab_action_coverage.get("tabs") != ["recon", "web", "network", "creds", "exploit", "post", "osint", "report", "stash"]:
        raise AssertionError(f"/qa/tab-action-coverage tabs mismatch: {tab_action_coverage}")
    if tab_action_coverage.get("proofCount", 0) < 27:
        raise AssertionError(f"/qa/tab-action-coverage proof count mismatch: {tab_action_coverage}")
    expected_tab_action_surfaces = [
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
    if tab_action_coverage.get("tabActionSurfaces") != expected_tab_action_surfaces:
        raise AssertionError(f"/qa/tab-action-coverage surface list mismatch: {tab_action_coverage}")
    if tab_action_coverage.get("tabActionSurfaceCount") != len(expected_tab_action_surfaces):
        raise AssertionError(f"/qa/tab-action-coverage surface count mismatch: {tab_action_coverage}")
    if tab_action_coverage.get("tabActionSurfaceParity") is not True:
        raise AssertionError(f"/qa/tab-action-coverage surface parity mismatch: {tab_action_coverage}")
    if tab_action_coverage.get("tabActionSurfaceProofCount") != len(expected_tab_action_surfaces):
        raise AssertionError(f"/qa/tab-action-coverage surface proof count mismatch: {tab_action_coverage}")
    if tab_action_coverage.get("tabActionSurfaceProofParity") is not True:
        raise AssertionError(f"/qa/tab-action-coverage surface proof parity mismatch: {tab_action_coverage}")
    if "stashActions" not in (tab_action_coverage.get("actionStateKeys") or []):
        raise AssertionError(f"/qa/tab-action-coverage action state keys mismatch: {tab_action_coverage}")
    if chat_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/chat-coverage failed: {chat_coverage}")
    if chat_coverage.get("cacheResponseMethod") != "prefix-cache-l2-turboquant":
        raise AssertionError(f"/qa/chat-coverage cache method mismatch: {chat_coverage}")
    if chat_coverage.get("cacheResponsesInferenceMethod") != "prefix-cache-l2-turboquant":
        raise AssertionError(f"/qa/chat-coverage cache responses inference method mismatch: {chat_coverage}")
    if chat_coverage.get("newContextBehavior") != "clear-visible-chat-preserve-engine-cache-session":
        raise AssertionError(f"/qa/chat-coverage context behavior mismatch: {chat_coverage}")
    if chat_coverage.get("newModelSessionBehavior") != "new-context-window-preserve-engine-cache-session":
        raise AssertionError(f"/qa/chat-coverage new model session behavior mismatch: {chat_coverage}")
    if chat_coverage.get("headerCacheBadges") != ["ctx", "cache preserved", "prefix/l2/tq", "new ctx keeps cache"]:
        raise AssertionError(f"/qa/chat-coverage header cache badges mismatch: {chat_coverage}")
    if chat_coverage.get("headerCacheBadgeCount") != 4:
        raise AssertionError(f"/qa/chat-coverage header cache badge count mismatch: {chat_coverage}")
    if chat_coverage.get("headerCacheBadgeParity") is not True:
        raise AssertionError(f"/qa/chat-coverage header cache badge parity mismatch: {chat_coverage}")
    if chat_coverage.get("headerCacheBadgeProofCount") != 4:
        raise AssertionError(f"/qa/chat-coverage header cache badge proof count mismatch: {chat_coverage}")
    if chat_coverage.get("headerCacheBadgeProofParity") is not True:
        raise AssertionError(f"/qa/chat-coverage header cache badge proof parity mismatch: {chat_coverage}")
    if chat_coverage.get("cacheSessionIndicator") != "prefix/l2/tq":
        raise AssertionError(f"/qa/chat-coverage cache session indicator mismatch: {chat_coverage}")
    if chat_coverage.get("newContextSessionBoundary") != "new ctx keeps cache":
        raise AssertionError(f"/qa/chat-coverage new context boundary mismatch: {chat_coverage}")
    expected_cache_session_fields = [
        "cacheResponsesMethod",
        "cacheResponsesInferenceMethod",
        "sessionBoundaryMode",
        "newModelSessionBehavior",
        "prefixCache",
        "promptL2Disk",
        "pagedCache",
        "blockL2Disk",
        "turboQuantKV",
    ]
    if chat_coverage.get("cacheSessionFields") != expected_cache_session_fields:
        raise AssertionError(f"/qa/chat-coverage cache session fields mismatch: {chat_coverage}")
    if chat_coverage.get("cacheSessionFieldCount") != len(expected_cache_session_fields):
        raise AssertionError(f"/qa/chat-coverage cache session field count mismatch: {chat_coverage}")
    if chat_coverage.get("cacheSessionFieldParity") is not True:
        raise AssertionError(f"/qa/chat-coverage cache session field parity mismatch: {chat_coverage}")
    if chat_coverage.get("cacheSessionFieldProofCount") != len(expected_cache_session_fields):
        raise AssertionError(f"/qa/chat-coverage cache session field proof count mismatch: {chat_coverage}")
    if chat_coverage.get("cacheSessionFieldProofParity") is not True:
        raise AssertionError(f"/qa/chat-coverage cache session field proof parity mismatch: {chat_coverage}")
    if chat_coverage.get("proofCount", 0) < 15:
        raise AssertionError(f"/qa/chat-coverage proof count mismatch: {chat_coverage}")
    if "chatActions" not in (chat_coverage.get("stateKeys") or []):
        raise AssertionError(f"/qa/chat-coverage state key mismatch: {chat_coverage}")
    if coverage_index.get("ok") is not True:
        raise AssertionError(f"/qa/coverage-index failed: {coverage_index}")
    if coverage_index.get("endpointCount", 0) < 16:
        raise AssertionError(f"/qa/coverage-index endpoint count mismatch: {coverage_index}")
    if coverage_index.get("proofCount", 0) < 14:
        raise AssertionError(f"/qa/coverage-index proof count mismatch: {coverage_index}")
    index_groups = coverage_index.get("groups") or {}
    app_state_group = index_groups.get("appState") or {}
    if app_state_group.get("proofLedgerCount", 0) < 120:
        raise AssertionError(f"/qa/coverage-index proof ledger count mismatch: {coverage_index}")
    if app_state_group.get("proofCategorySurfaceCount") != 8:
        raise AssertionError(f"/qa/coverage-index proof category surface count mismatch: {coverage_index}")
    if app_state_group.get("proofLedgerCategoryOtherCount") != proof_ledger.get("categoryOtherCount"):
        raise AssertionError(f"/qa/coverage-index source proof other count mismatch: {coverage_index}")
    if app_state_group.get("auditProofLedgerCategoryOtherCount") != audit_ledger.get("proofLedgerCategoryOtherCount"):
        raise AssertionError(f"/qa/coverage-index audit source proof other count mismatch: {coverage_index}")
    if app_state_group.get("proofCategoryTotalCount") != proof_ledger.get("proofCount"):
        raise AssertionError(f"/qa/coverage-index proof category total mismatch: {coverage_index}")
    if app_state_group.get("proofCategoryParity") is not True:
        raise AssertionError(f"/qa/coverage-index proof category parity flag mismatch: {coverage_index}")
    if app_state_group.get("checkpointLedgerCount", 0) < 200:
        raise AssertionError(f"/qa/coverage-index checkpoint ledger count mismatch: {coverage_index}")
    if app_state_group.get("checkpoints") != checkpoint_ledger.get("checkpoints"):
        raise AssertionError(f"/qa/coverage-index checkpoint list mismatch: {coverage_index}")
    if app_state_group.get("completeCheckpoints") != checkpoint_ledger.get("completeCheckpoints"):
        raise AssertionError(f"/qa/coverage-index complete checkpoint list mismatch: {coverage_index}")
    if app_state_group.get("incompleteCheckpoints") != checkpoint_ledger.get("incompleteCheckpoints"):
        raise AssertionError(f"/qa/coverage-index incomplete checkpoint list mismatch: {coverage_index}")
    if app_state_group.get("auditLedgerCount", 0) < 300:
        raise AssertionError(f"/qa/coverage-index audit ledger count mismatch: {coverage_index}")
    if app_state_group.get("auditLiveProofOkCount") != audit_ledger.get("liveProofOkCount"):
        raise AssertionError(f"/qa/coverage-index audit live proof ok count mismatch: {coverage_index}")
    if app_state_group.get("auditFailedLiveProofCount") != audit_ledger.get("failedLiveProofCount"):
        raise AssertionError(f"/qa/coverage-index audit failed live proof count mismatch: {coverage_index}")
    if app_state_group.get("auditFailedLiveProofs") != audit_ledger.get("failedLiveProofs"):
        raise AssertionError(f"/qa/coverage-index audit failed live proof list mismatch: {coverage_index}")
    if app_state_group.get("artifactLedgerVisualManifests") != artifact_ledger.get("visualManifests"):
        raise AssertionError(f"/qa/coverage-index artifact visual manifest list mismatch: {coverage_index}")
    if app_state_group.get("artifactLedgerVisualCaptureStatus") != artifact_ledger.get("visualCaptureStatus"):
        raise AssertionError(f"/qa/coverage-index artifact visual capture status mismatch: {coverage_index}")
    if app_state_group.get("artifactLedgerLiveProofs") != artifact_ledger.get("liveProofs"):
        raise AssertionError(f"/qa/coverage-index artifact live proof list mismatch: {coverage_index}")
    if app_state_group.get("artifactLedgerLiveProofStatus") != artifact_ledger.get("liveProofStatus"):
        raise AssertionError(f"/qa/coverage-index artifact live proof status mismatch: {coverage_index}")
    if app_state_group.get("missingVisualCaptures") != artifact_ledger.get("missingVisualCaptures"):
        raise AssertionError(f"/qa/coverage-index missing visual capture list mismatch: {coverage_index}")
    if app_state_group.get("currentGapCount", -1) != 1:
        raise AssertionError(f"/qa/coverage-index current gap count mismatch: {coverage_index}")
    if app_state_group.get("gapContracts") != gap_ledger.get("gapContracts"):
        raise AssertionError(f"/qa/coverage-index gap contract map mismatch: {coverage_index}")
    runtime_group = index_groups.get("runtimeAndCache") or {}
    if runtime_group.get("cacheComponentProofs") != runtime_coverage.get("cacheComponentProofs"):
        raise AssertionError(f"/qa/coverage-index runtime cache component proof map mismatch: {coverage_index}")
    settings_visuals_group = index_groups.get("settingsAndVisuals") or {}
    chat_context_group = index_groups.get("chatAndContext") or {}
    if chat_context_group.get("headerCacheBadgeProofs") != chat_coverage.get("headerCacheBadgeProofs"):
        raise AssertionError(f"/qa/coverage-index header cache badge proof map mismatch: {coverage_index}")
    if chat_context_group.get("cacheSessionFieldProofs") != chat_coverage.get("cacheSessionFieldProofs"):
        raise AssertionError(f"/qa/coverage-index cache session field proof map mismatch: {coverage_index}")
    if chat_context_group.get("retrievalSourceProofs") != context_coverage.get("retrievalSourceProofs"):
        raise AssertionError(f"/qa/coverage-index retrieval source proof map mismatch: {coverage_index}")
    if chat_context_group.get("contextDeliveryModeProofs") != context_coverage.get("contextDeliveryModeProofs"):
        raise AssertionError(f"/qa/coverage-index context delivery mode proof map mismatch: {coverage_index}")
    if settings_visuals_group.get("settingsSurfaceProofs") != settings_coverage.get("settingsSurfaceProofs"):
        raise AssertionError(f"/qa/coverage-index settings surface proof map mismatch: {coverage_index}")
    if settings_visuals_group.get("visualSurfaceProofs") != visual_coverage.get("visualSurfaceProofs"):
        raise AssertionError(f"/qa/coverage-index visual surface proof map mismatch: {coverage_index}")
    tools_parsers_group = index_groups.get("toolsAndParsers") or {}
    if tools_parsers_group.get("tabActivityStatusProofs") != tool_flow_coverage.get("tabActivityStatusProofs"):
        raise AssertionError(f"/qa/coverage-index tool tab activity proof map mismatch: {coverage_index}")
    if tools_parsers_group.get("toolVisualSurfaceProofs") != tool_flow_coverage.get("toolVisualSurfaceProofs"):
        raise AssertionError(f"/qa/coverage-index tool visual surface proof map mismatch: {coverage_index}")
    expected_family_fanout_tools = {
        "recon": "nmap",
        "web": "nuclei",
        "network": "netexec",
        "creds": "hashcat",
        "exploit": "metasploit",
        "post": "linpeas",
        "osint": "gowitness",
    }
    if tools_parsers_group.get("familyFanoutTools") != expected_family_fanout_tools:
        raise AssertionError(f"/qa/coverage-index family fanout tool map mismatch: {coverage_index}")
    expected_structured_parser_tools = [
        "arjun", "dalfox", "dnsx", "exiftool", "feroxbuster", "ffuf",
        "gowitness", "graphqlmap", "haiti", "hashcat", "holehe", "httpx",
        "hydra", "impacket", "jwt_tool", "katana", "linpeas", "masscan",
        "metasploit", "netexec", "nmap", "nuclei", "sherlock", "snmpwalk",
        "sqlmap", "subfinder", "testssl", "theharvester", "trufflehog", "wpscan",
    ]
    if tools_parsers_group.get("resultParserStructuredTools") != expected_structured_parser_tools:
        raise AssertionError(f"/qa/coverage-index structured parser tool set mismatch: {coverage_index}")
    if tools_parsers_group.get("resultParserRawOnlyTools") != ["bettercap", "chisel", "pwncat", "sliver", "tshark"]:
        raise AssertionError(f"/qa/coverage-index raw-only parser tool set mismatch: {coverage_index}")
    if ((index_groups.get("tabsAndSessions") or {}).get("actionStateKeyCount", 0)) < 26:
        raise AssertionError(f"/qa/coverage-index action state key count mismatch: {coverage_index}")
    tabs_sessions_group = index_groups.get("tabsAndSessions") or {}
    if tabs_sessions_group.get("subtabTabs") != subtab_coverage.get("tabs"):
        raise AssertionError(f"/qa/coverage-index subtab tab map mismatch: {coverage_index}")
    if tabs_sessions_group.get("subtabProofCount") != subtab_coverage.get("proofCount"):
        raise AssertionError(f"/qa/coverage-index subtab proof count mismatch: {coverage_index}")
    if tabs_sessions_group.get("sessionWorkflowSurfaceProofs") != session_coverage.get("sessionWorkflowSurfaceProofs"):
        raise AssertionError(f"/qa/coverage-index session workflow proof map mismatch: {coverage_index}")
    if tabs_sessions_group.get("tabActionSurfaceProofs") != tab_action_coverage.get("tabActionSurfaceProofs"):
        raise AssertionError(f"/qa/coverage-index tab action proof map mismatch: {coverage_index}")
    if tabs_sessions_group.get("agentLoopPhaseProofs") != agent_loop_coverage.get("loopPhaseProofs"):
        raise AssertionError(f"/qa/coverage-index agent loop phase proof map mismatch: {coverage_index}")
    if tabs_sessions_group.get("tabActivityStatusProofs") != tool_flow_coverage.get("tabActivityStatusProofs"):
        raise AssertionError(f"/qa/coverage-index tab activity status proof map mismatch: {coverage_index}")
    if tabs_sessions_group.get("agentLoopPhaseProofCount") != agent_loop_coverage.get("loopPhaseProofCount"):
        raise AssertionError(f"/qa/coverage-index agent loop phase proof count mismatch: {coverage_index}")
    if tabs_sessions_group.get("agentLoopPhaseProofParity") != agent_loop_coverage.get("loopPhaseProofParity"):
        raise AssertionError(f"/qa/coverage-index agent loop phase proof parity mismatch: {coverage_index}")
    if proof_ledger.get("ok") is not True or proof_ledger.get("proofCount", 0) < 120:
        raise AssertionError(f"/qa/proof-ledger count mismatch: {proof_ledger}")
    if artifact_ledger.get("ok") is not True:
        raise AssertionError(f"/qa/artifact-ledger failed: {artifact_ledger}")
    if artifact_ledger.get("visualManifestCount", 0) < 22:
        raise AssertionError(f"/qa/artifact-ledger visual manifest count mismatch: {artifact_ledger}")
    if artifact_ledger.get("missingVisualCaptures") != []:
        raise AssertionError(f"/qa/artifact-ledger reports missing captures: {artifact_ledger}")
    if checkpoint_ledger.get("ok") is not True or checkpoint_ledger.get("checkpointCount", 0) < 200:
        raise AssertionError(f"/qa/checkpoint-ledger count mismatch: {checkpoint_ledger}")
    if not checkpoint_ledger.get("latestCheckpoint", "").endswith(".md"):
        raise AssertionError(f"/qa/checkpoint-ledger latest checkpoint mismatch: {checkpoint_ledger}")
    if audit_ledger.get("ok") is not True:
        raise AssertionError(f"/qa/audit-ledger failed: {audit_ledger}")
    if audit_ledger.get("proofCount") != proof_ledger.get("proofCount"):
        raise AssertionError(f"/qa/audit-ledger proof count mismatch: {audit_ledger}")
    if audit_ledger.get("visualManifestCount") != artifact_ledger.get("visualManifestCount"):
        raise AssertionError(f"/qa/audit-ledger visual manifest count mismatch: {audit_ledger}")
    if audit_ledger.get("checkpointCount") != checkpoint_ledger.get("checkpointCount"):
        raise AssertionError(f"/qa/audit-ledger checkpoint count mismatch: {audit_ledger}")
    if audit_ledger.get("totalLedgerItemCount", 0) < 300:
        raise AssertionError(f"/qa/audit-ledger total count mismatch: {audit_ledger}")
    if gap_ledger.get("ok") is not True:
        raise AssertionError(f"/qa/gap-ledger failed: {gap_ledger}")
    if gap_ledger.get("currentGapCount") != 1:
        raise AssertionError(f"/qa/gap-ledger current gap count mismatch: {gap_ledger}")
    if set(gap_ledger.get("supportedFamilies") or []) != {"qwen", "minimax"}:
        raise AssertionError(f"/qa/gap-ledger supported families mismatch: {gap_ledger}")
    if gap_ledger.get("unsupportedMultimodalBlocked") is not True:
        raise AssertionError(f"/qa/gap-ledger Qwen VL block mismatch: {gap_ledger}")


def run() -> None:
    assert_removed_profile_code()
    assert_required_context_hooks()

    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_testserver_smoke()
        print("app-qa-matrix-smoke proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"app-qa-matrix-smoke proof failed: {exc}", flush=True)
        raise SystemExit(1)
