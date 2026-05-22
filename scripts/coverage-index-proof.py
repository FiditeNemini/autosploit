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

EXPECTED_FAMILY_FANOUT_TOOLS = {
    "recon": "nmap",
    "web": "nuclei",
    "network": "netexec",
    "creds": "hashcat",
    "exploit": "metasploit",
    "post": "linpeas",
    "osint": "gowitness",
}

EXPECTED_RESULT_PARSER_STRUCTURED_TOOLS = [
    "arjun",
    "dalfox",
    "dnsx",
    "exiftool",
    "feroxbuster",
    "ffuf",
    "gowitness",
    "graphqlmap",
    "haiti",
    "hashcat",
    "holehe",
    "httpx",
    "hydra",
    "impacket",
    "jwt_tool",
    "katana",
    "linpeas",
    "masscan",
    "metasploit",
    "netexec",
    "nmap",
    "nuclei",
    "sherlock",
    "snmpwalk",
    "sqlmap",
    "subfinder",
    "testssl",
    "theharvester",
    "trufflehog",
    "wpscan",
]

EXPECTED_RESULT_PARSER_RAW_ONLY_TOOLS = [
    "bettercap",
    "chisel",
    "pwncat",
    "sliver",
    "tshark",
]


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
    seeded = request("POST", "/qa/seed-result-parser-fixture")
    if seeded.get("ok") is not True:
        raise AssertionError(f"result parser fixture seed failed: {seeded}")
    state = request("GET", "/state")
    index = request("GET", "/qa/coverage-index")
    proof = request("GET", "/qa/proof-ledger")
    artifact = request("GET", "/qa/artifact-ledger")
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
    if app_state_group.get("artifactLedgerVisualManifests") != artifact.get("visualManifests"):
        raise AssertionError(f"coverage index app state artifact visual manifests mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerVisualCaptureStatus") != artifact.get("visualCaptureStatus"):
        raise AssertionError(f"coverage index app state artifact visual capture status mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerLiveProofCount", 0) < 18:
        raise AssertionError(f"coverage index app state artifact live count mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerLiveProofs") != artifact.get("liveProofs"):
        raise AssertionError(f"coverage index app state artifact live proofs mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerLiveProofStatus") != artifact.get("liveProofStatus"):
        raise AssertionError(f"coverage index app state artifact live proof status mismatch: {app_state_group}")
    if app_state_group.get("missingVisualCaptureCount", 1) != 0:
        raise AssertionError(f"coverage index app state missing visual captures: {app_state_group}")
    if app_state_group.get("missingVisualCaptures") != artifact.get("missingVisualCaptures"):
        raise AssertionError(f"coverage index app state missing visual capture list mismatch: {app_state_group}")
    if app_state_group.get("checkpointLedgerCount", 0) < 200:
        raise AssertionError(f"coverage index app state checkpoint ledger count mismatch: {app_state_group}")
    if app_state_group.get("checkpoints") != checkpoint.get("checkpoints"):
        raise AssertionError(f"coverage index app state checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("completeCheckpointCount") != checkpoint.get("completeCheckpointCount"):
        raise AssertionError(f"coverage index app state complete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("completeCheckpoints") != checkpoint.get("completeCheckpoints"):
        raise AssertionError(f"coverage index app state complete checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("incompleteCheckpointCount") != len(checkpoint.get("incompleteCheckpoints") or []):
        raise AssertionError(f"coverage index app state incomplete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("incompleteCheckpoints") != checkpoint.get("incompleteCheckpoints"):
        raise AssertionError(f"coverage index app state incomplete checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("checkpointCompletionRatio") != checkpoint.get("checkpointCompletionRatio"):
        raise AssertionError(f"coverage index app state checkpoint ratio mismatch: {app_state_group}")
    if app_state_group.get("latestCheckpoint") != checkpoint.get("latestCheckpoint"):
        raise AssertionError(f"coverage index app state latest checkpoint mismatch: {app_state_group}")
    if app_state_group.get("latestCheckpointNumber") != checkpoint.get("latestCheckpointNumber"):
        raise AssertionError(f"coverage index app state latest checkpoint number mismatch: {app_state_group}")
    if app_state_group.get("auditLedgerCount", 0) < 300:
        raise AssertionError(f"coverage index app state audit ledger count mismatch: {app_state_group}")
    if app_state_group.get("auditVisualManifestCount") != audit.get("visualManifestCount"):
        raise AssertionError(f"coverage index app state audit visual manifest count mismatch: {app_state_group}")
    if app_state_group.get("auditVisualCaptureCount") != audit.get("visualCaptureCount"):
        raise AssertionError(f"coverage index app state audit visual capture count mismatch: {app_state_group}")
    if app_state_group.get("auditMissingVisualCaptureCount") != audit.get("missingVisualCaptureCount"):
        raise AssertionError(f"coverage index app state audit missing visual capture count mismatch: {app_state_group}")
    if app_state_group.get("auditMissingVisualCaptures") != audit.get("missingVisualCaptures"):
        raise AssertionError(f"coverage index app state audit missing visual capture list mismatch: {app_state_group}")
    if app_state_group.get("auditLiveProofCount") != audit.get("liveProofCount"):
        raise AssertionError(f"coverage index app state audit live proof count mismatch: {app_state_group}")
    if app_state_group.get("auditLiveProofOkCount") != audit.get("liveProofOkCount"):
        raise AssertionError(f"coverage index app state audit live proof ok count mismatch: {app_state_group}")
    if app_state_group.get("auditFailedLiveProofCount") != audit.get("failedLiveProofCount"):
        raise AssertionError(f"coverage index app state audit failed live proof count mismatch: {app_state_group}")
    if app_state_group.get("auditFailedLiveProofs") != audit.get("failedLiveProofs"):
        raise AssertionError(f"coverage index app state audit failed live proof list mismatch: {app_state_group}")
    if app_state_group.get("auditCheckpointCount") != audit.get("checkpointCount"):
        raise AssertionError(f"coverage index app state audit checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("auditCompleteCheckpointCount") != audit.get("completeCheckpointCount"):
        raise AssertionError(f"coverage index app state audit complete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("auditCompleteCheckpoints") != audit.get("completeCheckpoints"):
        raise AssertionError(f"coverage index app state audit complete checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("auditIncompleteCheckpointCount") != audit.get("incompleteCheckpointCount"):
        raise AssertionError(f"coverage index app state audit incomplete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("auditIncompleteCheckpoints") != audit.get("incompleteCheckpoints"):
        raise AssertionError(f"coverage index app state audit incomplete checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("auditCurrentGapCount") != audit.get("currentGapCount"):
        raise AssertionError(f"coverage index app state audit current gap count mismatch: {app_state_group}")
    if app_state_group.get("auditGapSource") != audit.get("gapSource"):
        raise AssertionError(f"coverage index app state audit gap source mismatch: {app_state_group}")
    if app_state_group.get("auditGapSourceDerived") != audit.get("gapSourceDerived"):
        raise AssertionError(f"coverage index app state audit gap source-derived flag mismatch: {app_state_group}")
    if app_state_group.get("auditGapSourcePathExists") != audit.get("gapSourcePathExists"):
        raise AssertionError(f"coverage index app state audit gap source path flag mismatch: {app_state_group}")
    if app_state_group.get("auditCurrentGaps") != audit.get("currentGaps"):
        raise AssertionError(f"coverage index app state audit current gap list mismatch: {app_state_group}")
    if app_state_group.get("auditNextGap") != audit.get("nextGap"):
        raise AssertionError(f"coverage index app state audit next gap mismatch: {app_state_group}")
    if app_state_group.get("auditGapSupportedFamilies") != audit.get("gapSupportedFamilies"):
        raise AssertionError(f"coverage index app state audit gap supported families mismatch: {app_state_group}")
    if app_state_group.get("auditUnsupportedMultimodalBlocked") != audit.get("unsupportedMultimodalBlocked"):
        raise AssertionError(f"coverage index app state audit unsupported multimodal block mismatch: {app_state_group}")
    if app_state_group.get("auditOpenGapIds") != audit.get("openGapIds"):
        raise AssertionError(f"coverage index app state audit open gap ids mismatch: {app_state_group}")
    if app_state_group.get("auditGapContracts") != audit.get("gapContracts"):
        raise AssertionError(f"coverage index app state audit gap contracts mismatch: {app_state_group}")
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
    if app_state_group.get("gapSource") != gap.get("source"):
        raise AssertionError(f"coverage index app state gap source mismatch: {app_state_group}")
    if app_state_group.get("gapSourceDerived") != gap.get("sourceDerived"):
        raise AssertionError(f"coverage index app state gap source-derived flag mismatch: {app_state_group}")
    if app_state_group.get("gapSourcePathExists") != gap.get("sourcePathExists"):
        raise AssertionError(f"coverage index app state gap source path flag mismatch: {app_state_group}")
    if app_state_group.get("currentGaps") != gap.get("currentGaps"):
        raise AssertionError(f"coverage index app state current gap list mismatch: {app_state_group}")
    if app_state_group.get("nextGap") != gap.get("nextGap"):
        raise AssertionError(f"coverage index app state next gap mismatch: {app_state_group}")
    if app_state_group.get("gapSupportedFamilies") != gap.get("supportedFamilies"):
        raise AssertionError(f"coverage index app state gap supported families mismatch: {app_state_group}")
    if app_state_group.get("unsupportedMultimodalBlocked") != gap.get("unsupportedMultimodalBlocked"):
        raise AssertionError(f"coverage index app state unsupported multimodal block mismatch: {app_state_group}")
    if app_state_group.get("openGapIds") != gap.get("openGapIds"):
        raise AssertionError(f"coverage index app state open gap ids mismatch: {app_state_group}")
    if app_state_group.get("gapContracts") != gap.get("gapContracts"):
        raise AssertionError(f"coverage index app state gap contracts mismatch: {app_state_group}")
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
    if runtime_group.get("runtimeContracts") != runtime_coverage.get("contracts"):
        raise AssertionError(f"coverage index runtime contract map mismatch: {runtime_group}")
    if runtime_group.get("runtimeContractCount") != len(runtime_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index runtime contract count mismatch: {runtime_group}")
    if runtime_group.get("runtimeRoutes") != runtime_coverage.get("routes"):
        raise AssertionError(f"coverage index runtime route list mismatch: {runtime_group}")
    if runtime_group.get("runtimeRouteCount") != len(runtime_coverage.get("routes") or []):
        raise AssertionError(f"coverage index runtime route count mismatch: {runtime_group}")
    if runtime_group.get("runtimeProofs") != runtime_coverage.get("proofs"):
        raise AssertionError(f"coverage index runtime proof list mismatch: {runtime_group}")
    if runtime_group.get("runtimeProofCount") != runtime_coverage.get("proofCount"):
        raise AssertionError(f"coverage index runtime proof count mismatch: {runtime_group}")
    if runtime_group.get("liveProofs") != runtime_coverage.get("liveProofs"):
        raise AssertionError(f"coverage index runtime live proof matrix mismatch: {runtime_group}")
    if runtime_group.get("liveProofArtifacts") != runtime_coverage.get("liveProofArtifacts"):
        raise AssertionError(f"coverage index runtime live proof artifact map mismatch: {runtime_group}")
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
    if runtime_group.get("cacheComponentProofs") != runtime_coverage.get("cacheComponentProofs"):
        raise AssertionError(f"coverage index runtime cache component proof map mismatch: {runtime_group}")
    if runtime_group.get("cacheComponentProofCount") != runtime_coverage.get("cacheComponentProofCount"):
        raise AssertionError(f"coverage index runtime cache component proof count mismatch: {runtime_group}")
    if runtime_group.get("cacheComponentProofParity") != runtime_coverage.get("cacheComponentProofParity"):
        raise AssertionError(f"coverage index runtime cache component proof parity mismatch: {runtime_group}")
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
    if chat_context_group.get("headerCacheBadgeProofs") != chat_coverage.get("headerCacheBadgeProofs"):
        raise AssertionError(f"coverage index chat/context header cache badge proof map mismatch: {chat_context_group}")
    if chat_context_group.get("headerCacheBadgeProofCount") != chat_coverage.get("headerCacheBadgeProofCount"):
        raise AssertionError(f"coverage index chat/context header cache badge proof count mismatch: {chat_context_group}")
    if chat_context_group.get("headerCacheBadgeProofParity") != chat_coverage.get("headerCacheBadgeProofParity"):
        raise AssertionError(f"coverage index chat/context header cache badge proof parity mismatch: {chat_context_group}")
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
    if chat_context_group.get("cacheSessionFieldProofs") != chat_coverage.get("cacheSessionFieldProofs"):
        raise AssertionError(f"coverage index chat/context cache session field proof map mismatch: {chat_context_group}")
    if chat_context_group.get("cacheSessionFieldProofCount") != chat_coverage.get("cacheSessionFieldProofCount"):
        raise AssertionError(f"coverage index chat/context cache session field proof count mismatch: {chat_context_group}")
    if chat_context_group.get("cacheSessionFieldProofParity") != chat_coverage.get("cacheSessionFieldProofParity"):
        raise AssertionError(f"coverage index chat/context cache session field proof parity mismatch: {chat_context_group}")
    if chat_context_group.get("chatRoutes") != chat_coverage.get("routes"):
        raise AssertionError(f"coverage index chat/context chat route list mismatch: {chat_context_group}")
    if chat_context_group.get("chatRouteCount") != len(chat_coverage.get("routes") or []):
        raise AssertionError(f"coverage index chat/context chat route count mismatch: {chat_context_group}")
    if chat_context_group.get("chatContracts") != chat_coverage.get("contracts"):
        raise AssertionError(f"coverage index chat/context chat contract map mismatch: {chat_context_group}")
    if chat_context_group.get("chatContractCount") != len(chat_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index chat/context chat contract count mismatch: {chat_context_group}")
    if chat_context_group.get("chatProofs") != chat_coverage.get("proofs"):
        raise AssertionError(f"coverage index chat/context chat proof list mismatch: {chat_context_group}")
    if chat_context_group.get("chatProofCount") != chat_coverage.get("proofCount"):
        raise AssertionError(f"coverage index chat/context chat proof count mismatch: {chat_context_group}")
    if chat_context_group.get("chatStateKeys") != chat_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index chat/context chat state-key list mismatch: {chat_context_group}")
    if chat_context_group.get("chatStateKeyCount") != len(chat_coverage.get("stateKeys") or []):
        raise AssertionError(f"coverage index chat/context chat state-key count mismatch: {chat_context_group}")
    context_coverage = request("GET", "/qa/context-coverage")
    if chat_context_group.get("searchToolName") != context_coverage.get("searchToolName"):
        raise AssertionError(f"coverage index chat/context search tool mismatch: {chat_context_group}")
    if chat_context_group.get("automaticInjectedContextCap") != context_coverage.get("automaticInjectedContextCap"):
        raise AssertionError(f"coverage index chat/context automatic context cap mismatch: {chat_context_group}")
    if chat_context_group.get("currentInjectedContextLimit") != context_coverage.get("currentInjectedContextLimit"):
        raise AssertionError(f"coverage index chat/context current context limit mismatch: {chat_context_group}")
    if chat_context_group.get("contextRoutes") != context_coverage.get("routes"):
        raise AssertionError(f"coverage index chat/context context route list mismatch: {chat_context_group}")
    if chat_context_group.get("contextRouteCount") != len(context_coverage.get("routes") or []):
        raise AssertionError(f"coverage index chat/context context route count mismatch: {chat_context_group}")
    if chat_context_group.get("contextContracts") != context_coverage.get("contracts"):
        raise AssertionError(f"coverage index chat/context context contract map mismatch: {chat_context_group}")
    if chat_context_group.get("contextContractCount") != len(context_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index chat/context context contract count mismatch: {chat_context_group}")
    if chat_context_group.get("contextProofs") != context_coverage.get("proofs"):
        raise AssertionError(f"coverage index chat/context context proof list mismatch: {chat_context_group}")
    if chat_context_group.get("contextProofCount") != context_coverage.get("proofCount"):
        raise AssertionError(f"coverage index chat/context context proof count mismatch: {chat_context_group}")
    if chat_context_group.get("contextStateKeys") != context_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index chat/context context state-key list mismatch: {chat_context_group}")
    if chat_context_group.get("contextStateKeyCount") != len(context_coverage.get("stateKeys") or []):
        raise AssertionError(f"coverage index chat/context context state-key count mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSources") != context_coverage.get("retrievalSources"):
        raise AssertionError(f"coverage index chat/context retrieval sources mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSourceCount") != context_coverage.get("retrievalSourceCount"):
        raise AssertionError(f"coverage index chat/context retrieval source count mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSourceParity") != context_coverage.get("retrievalSourceParity"):
        raise AssertionError(f"coverage index chat/context retrieval source parity mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSourceProofs") != context_coverage.get("retrievalSourceProofs"):
        raise AssertionError(f"coverage index chat/context retrieval source proof map mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSourceProofCount") != context_coverage.get("retrievalSourceProofCount"):
        raise AssertionError(f"coverage index chat/context retrieval source proof count mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSourceProofParity") != context_coverage.get("retrievalSourceProofParity"):
        raise AssertionError(f"coverage index chat/context retrieval source proof parity mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModes") != context_coverage.get("contextDeliveryModes"):
        raise AssertionError(f"coverage index chat/context delivery modes mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModeCount") != context_coverage.get("contextDeliveryModeCount"):
        raise AssertionError(f"coverage index chat/context delivery mode count mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModeParity") != context_coverage.get("contextDeliveryModeParity"):
        raise AssertionError(f"coverage index chat/context delivery mode parity mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModeProofs") != context_coverage.get("contextDeliveryModeProofs"):
        raise AssertionError(f"coverage index chat/context delivery mode proof map mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModeProofCount") != context_coverage.get("contextDeliveryModeProofCount"):
        raise AssertionError(f"coverage index chat/context delivery mode proof count mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModeProofParity") != context_coverage.get("contextDeliveryModeProofParity"):
        raise AssertionError(f"coverage index chat/context delivery mode proof parity mismatch: {chat_context_group}")
    settings_visuals_group = groups.get("settingsAndVisuals") or {}
    settings_coverage = request("GET", "/qa/settings-coverage")
    if settings_visuals_group.get("settingsSurfaces") != settings_coverage.get("settingsSurfaces"):
        raise AssertionError(f"coverage index settings surface list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceCount") != settings_coverage.get("settingsSurfaceCount"):
        raise AssertionError(f"coverage index settings surface count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceParity") != settings_coverage.get("settingsSurfaceParity"):
        raise AssertionError(f"coverage index settings surface parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceProofs") != settings_coverage.get("settingsSurfaceProofs"):
        raise AssertionError(f"coverage index settings surface proof map mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceProofCount") != settings_coverage.get("settingsSurfaceProofCount"):
        raise AssertionError(f"coverage index settings surface proof count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceProofParity") != settings_coverage.get("settingsSurfaceProofParity"):
        raise AssertionError(f"coverage index settings surface proof parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsCategories") != settings_coverage.get("categories"):
        raise AssertionError(f"coverage index settings category list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsCategoryCount") != settings_coverage.get("categoryCount"):
        raise AssertionError(f"coverage index settings category count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsCurrentCategory") != settings_coverage.get("currentCategory"):
        raise AssertionError(f"coverage index settings current category mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsRoutes") != settings_coverage.get("routes"):
        raise AssertionError(f"coverage index settings route list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsRouteCount") != len(settings_coverage.get("routes") or []):
        raise AssertionError(f"coverage index settings route count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsContracts") != settings_coverage.get("contracts"):
        raise AssertionError(f"coverage index settings contract map mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsContractCount") != len(settings_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index settings contract count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsProofs") != settings_coverage.get("proofs"):
        raise AssertionError(f"coverage index settings proof list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsProofCount") != settings_coverage.get("proofCount"):
        raise AssertionError(f"coverage index settings proof count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsVisualManifests") != settings_coverage.get("visualManifests"):
        raise AssertionError(f"coverage index settings visual manifest list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsVisualManifestCount", 0) < 6:
        raise AssertionError(f"coverage index settings visual manifest count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualManifestCount", 0) < 22:
        raise AssertionError(f"coverage index visual manifest count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("actualCaptureCount", 0) < 48:
        raise AssertionError(f"coverage index visual capture count mismatch: {settings_visuals_group}")
    visual_coverage = request("GET", "/qa/visual-coverage")
    if settings_visuals_group.get("visualRoutes") != visual_coverage.get("routes"):
        raise AssertionError(f"coverage index visual route list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualRouteCount") != len(visual_coverage.get("routes") or []):
        raise AssertionError(f"coverage index visual route count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualContracts") != visual_coverage.get("contracts"):
        raise AssertionError(f"coverage index visual contract map mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualContractCount") != len(visual_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index visual contract count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualProofs") != visual_coverage.get("proofs"):
        raise AssertionError(f"coverage index visual proof list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualProofCount") != visual_coverage.get("proofCount"):
        raise AssertionError(f"coverage index visual proof count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualManifests") != visual_coverage.get("manifests"):
        raise AssertionError(f"coverage index visual manifest list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("minimumCaptureCount") != visual_coverage.get("minimumCaptureCount"):
        raise AssertionError(f"coverage index visual minimum capture count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaces") != visual_coverage.get("visualSurfaces"):
        raise AssertionError(f"coverage index visual surface list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceCount") != visual_coverage.get("visualSurfaceCount"):
        raise AssertionError(f"coverage index visual surface count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceParity") != visual_coverage.get("visualSurfaceParity"):
        raise AssertionError(f"coverage index visual surface parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceProofs") != visual_coverage.get("visualSurfaceProofs"):
        raise AssertionError(f"coverage index visual surface proof map mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceProofCount") != visual_coverage.get("visualSurfaceProofCount"):
        raise AssertionError(f"coverage index visual surface proof count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceProofParity") != visual_coverage.get("visualSurfaceProofParity"):
        raise AssertionError(f"coverage index visual surface proof parity mismatch: {settings_visuals_group}")
    tools_parsers_group = groups.get("toolsAndParsers") or {}
    if tools_parsers_group.get("toolCount", 0) < 38:
        raise AssertionError(f"coverage index tools/parsers tool count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("callbackCount", 0) < 3:
        raise AssertionError(f"coverage index tools/parsers callback count mismatch: {tools_parsers_group}")
    tool_coverage = request("GET", "/qa/tool-coverage")
    if tools_parsers_group.get("toolRegistryTools") != tool_coverage.get("tools"):
        raise AssertionError(f"coverage index tools/parsers tool registry list mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolRegistryTabs") != tool_coverage.get("tabs"):
        raise AssertionError(f"coverage index tools/parsers tool registry tab list mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolRegistryFailures") != tool_coverage.get("failures"):
        raise AssertionError(f"coverage index tools/parsers tool registry failures mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolRegistryFailureCount") != len(tool_coverage.get("failures") or []):
        raise AssertionError(f"coverage index tools/parsers tool registry failure count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("alwaysVisibleToolCount") != tool_coverage.get("alwaysVisibleCount"):
        raise AssertionError(f"coverage index tools/parsers always-visible tool count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("boundedCatalogueLimit") != tool_coverage.get("boundedCatalogueLimit"):
        raise AssertionError(f"coverage index tools/parsers bounded catalogue limit mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("familyFanoutCount", 0) < 7:
        raise AssertionError(f"coverage index tools/parsers family fanout count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("familyFanoutTools") != EXPECTED_FAMILY_FANOUT_TOOLS:
        raise AssertionError(f"coverage index tools/parsers family fanout tool map mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultParserStructuredTools") != EXPECTED_RESULT_PARSER_STRUCTURED_TOOLS:
        raise AssertionError(f"coverage index tools/parsers structured parser tool set mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultParserRawOnlyTools") != EXPECTED_RESULT_PARSER_RAW_ONLY_TOOLS:
        raise AssertionError(f"coverage index tools/parsers raw-only parser tool set mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("stateKeyCount", 0) < 5:
        raise AssertionError(f"coverage index tools/parsers state key count mismatch: {tools_parsers_group}")
    tool_flow = request("GET", "/qa/tool-flow-coverage")
    result_parser = request("GET", "/qa/result-parser-coverage")
    if tools_parsers_group.get("resultParserCounts") != result_parser.get("counts"):
        raise AssertionError(f"coverage index tools/parsers result-parser counts mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultParserParsedTools") != result_parser.get("parsedTools"):
        raise AssertionError(f"coverage index tools/parsers result-parser parsed tools mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultParserRawOnlyParsedTools") != result_parser.get("rawOnlyTools"):
        raise AssertionError(f"coverage index tools/parsers result-parser raw-only tools mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultParserFailures") != result_parser.get("failures"):
        raise AssertionError(f"coverage index tools/parsers result-parser failures mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultParserFailureCount") != len(result_parser.get("failures") or []):
        raise AssertionError(f"coverage index tools/parsers result-parser failure count mismatch: {tools_parsers_group}")
    for field in (
        "subdomains",
        "webUrls",
        "vulnSources",
        "vulnTitles",
        "ports",
        "networkHosts",
        "osintPlatforms",
        "postLabels",
        "rawTools",
    ):
        aggregate_field = "resultParser" + field[:1].upper() + field[1:]
        if tools_parsers_group.get(aggregate_field) != result_parser.get(field):
            raise AssertionError(f"coverage index tools/parsers {aggregate_field} mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowProofCount") != tool_flow.get("proofCount"):
        raise AssertionError(f"coverage index tools/parsers tool-flow proof count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowProofs") != tool_flow.get("proofs"):
        raise AssertionError(f"coverage index tools/parsers tool-flow proof list mismatch: {tools_parsers_group}")
    proof_files_exist = all((ROOT / "scripts" / name).is_file() for name in (tool_flow.get("proofs") or []))
    if tools_parsers_group.get("toolFlowProofFileParity") is not proof_files_exist:
        raise AssertionError(f"coverage index tools/parsers tool-flow proof-file parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowRoutes") != tool_flow.get("routes"):
        raise AssertionError(f"coverage index tools/parsers tool-flow routes mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowRouteCount") != len(tool_flow.get("routes") or []):
        raise AssertionError(f"coverage index tools/parsers tool-flow route count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowFamilies") != tool_flow.get("families"):
        raise AssertionError(f"coverage index tools/parsers tool-flow families mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowFamilyCount") != len(tool_flow.get("families") or []):
        raise AssertionError(f"coverage index tools/parsers tool-flow family count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowStateKeys") != tool_flow.get("stateKeys"):
        raise AssertionError(f"coverage index tools/parsers tool-flow state keys mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowContracts") != tool_flow.get("contracts"):
        raise AssertionError(f"coverage index tools/parsers tool-flow contracts mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowContractCount") != len(tool_flow.get("contracts") or {}):
        raise AssertionError(f"coverage index tools/parsers tool-flow contract count mismatch: {tools_parsers_group}")
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
    if tools_parsers_group.get("tabActivityStatusProofs") != tool_flow.get("tabActivityStatusProofs"):
        raise AssertionError(f"coverage index tools/parsers tab activity status proof map mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityStatusProofCount") != tool_flow.get("tabActivityStatusProofCount"):
        raise AssertionError(f"coverage index tools/parsers tab activity status proof count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityStatusProofParity") != tool_flow.get("tabActivityStatusProofParity"):
        raise AssertionError(f"coverage index tools/parsers tab activity status proof parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaces") != tool_flow.get("toolVisualSurfaces"):
        raise AssertionError(f"coverage index tools/parsers visual surfaces mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaceCount") != tool_flow.get("toolVisualSurfaceCount"):
        raise AssertionError(f"coverage index tools/parsers visual surface count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaceParity") != tool_flow.get("toolVisualSurfaceParity"):
        raise AssertionError(f"coverage index tools/parsers visual surface parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaceProofs") != tool_flow.get("toolVisualSurfaceProofs"):
        raise AssertionError(f"coverage index tools/parsers visual surface proof map mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaceProofCount") != tool_flow.get("toolVisualSurfaceProofCount"):
        raise AssertionError(f"coverage index tools/parsers visual surface proof count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaceProofParity") != tool_flow.get("toolVisualSurfaceProofParity"):
        raise AssertionError(f"coverage index tools/parsers visual surface proof parity mismatch: {tools_parsers_group}")
    tabs_sessions_group = groups.get("tabsAndSessions") or {}
    if tabs_sessions_group.get("interactionModeCount", 0) < 3:
        raise AssertionError(f"coverage index tabs/sessions mode count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("coveredTabCount", 0) < 9:
        raise AssertionError(f"coverage index tabs/sessions tab count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("stateKeyCount", 0) < 12:
        raise AssertionError(f"coverage index tabs/sessions state key count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("actionStateKeyCount", 0) < 26:
        raise AssertionError(f"coverage index tabs/sessions action state key count mismatch: {tabs_sessions_group}")
    subtab_coverage = request("GET", "/qa/subtab-coverage")
    if tabs_sessions_group.get("subtabTabs") != subtab_coverage.get("tabs"):
        raise AssertionError(f"coverage index tabs/sessions subtab tab map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("subtabProofCount") != subtab_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions subtab proof count mismatch: {tabs_sessions_group}")
    agent_loop = request("GET", "/qa/agent-loop-coverage")
    if tabs_sessions_group.get("agentLoopStateKeyCount") != agent_loop.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop state key count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopCurrentMode") != agent_loop.get("currentMode"):
        raise AssertionError(f"coverage index tabs/sessions agent loop current mode mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopMaxIterations") != agent_loop.get("maxIterations"):
        raise AssertionError(f"coverage index tabs/sessions agent loop max iterations mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopProofCount") != agent_loop.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopVisualStateKeys") != agent_loop.get("visualStateKeys"):
        raise AssertionError(f"coverage index tabs/sessions agent loop visual state keys mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopVisualStateKeyCount") != agent_loop.get("visualStateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop visual state key count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhases") != agent_loop.get("loopPhases"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phases mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseCount") != agent_loop.get("loopPhaseCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseParity") != agent_loop.get("loopPhaseParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseProofs") != agent_loop.get("loopPhaseProofs"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase proof map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseProofCount") != agent_loop.get("loopPhaseProofCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseProofParity") != agent_loop.get("loopPhaseProofParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase proof parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopModes") != agent_loop.get("modes"):
        raise AssertionError(f"coverage index tabs/sessions agent loop modes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopAgents") != agent_loop.get("agents"):
        raise AssertionError(f"coverage index tabs/sessions agent loop agent contract mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopRoutes") != agent_loop.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions agent loop routes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopRouteCount") != len(agent_loop.get("routes") or []):
        raise AssertionError(f"coverage index tabs/sessions agent loop route count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopContracts") != agent_loop.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions agent loop contracts mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopContractCount") != len(agent_loop.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions agent loop contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopActionTelemetryFields") != agent_loop.get("actionTelemetryFields"):
        raise AssertionError(f"coverage index tabs/sessions agent loop telemetry fields mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopActionTelemetryFieldCount") != len(agent_loop.get("actionTelemetryFields") or []):
        raise AssertionError(f"coverage index tabs/sessions agent loop telemetry count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatuses") != tool_flow.get("tabActivityStatuses"):
        raise AssertionError(f"coverage index tabs/sessions tab activity statuses mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatusCount") != tool_flow.get("tabActivityStatusCount"):
        raise AssertionError(f"coverage index tabs/sessions tab activity status count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatusParity") != tool_flow.get("tabActivityStatusParity"):
        raise AssertionError(f"coverage index tabs/sessions tab activity status parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityIndicatorContract") != tool_flow.get("tabActivityIndicatorContract"):
        raise AssertionError(f"coverage index tabs/sessions tab activity indicator contract mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatusProofs") != tool_flow.get("tabActivityStatusProofs"):
        raise AssertionError(f"coverage index tabs/sessions tab activity status proof map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatusProofCount") != tool_flow.get("tabActivityStatusProofCount"):
        raise AssertionError(f"coverage index tabs/sessions tab activity status proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatusProofParity") != tool_flow.get("tabActivityStatusProofParity"):
        raise AssertionError(f"coverage index tabs/sessions tab activity status proof parity mismatch: {tabs_sessions_group}")
    session_coverage = request("GET", "/qa/session-coverage")
    if tabs_sessions_group.get("sessionRoutes") != session_coverage.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions session route list mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionRouteCount") != len(session_coverage.get("routes") or []):
        raise AssertionError(f"coverage index tabs/sessions session route count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionContracts") != session_coverage.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions session contract map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionContractCount") != len(session_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions session contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionProofs") != session_coverage.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions session proof list mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionProofCount") != session_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions session proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionStateKeys") != session_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index tabs/sessions session state-key list mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionStateKeyCount") != len(session_coverage.get("stateKeys") or []):
        raise AssertionError(f"coverage index tabs/sessions session state-key count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowSurfaces") != session_coverage.get("sessionWorkflowSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions workflow surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowSurfaceCount") != session_coverage.get("sessionWorkflowSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions workflow surface count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowSurfaceParity") != session_coverage.get("sessionWorkflowSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions workflow surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowSurfaceProofs") != session_coverage.get("sessionWorkflowSurfaceProofs"):
        raise AssertionError(f"coverage index tabs/sessions workflow surface proof map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowSurfaceProofCount") != session_coverage.get("sessionWorkflowSurfaceProofCount"):
        raise AssertionError(f"coverage index tabs/sessions workflow surface proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowSurfaceProofParity") != session_coverage.get("sessionWorkflowSurfaceProofParity"):
        raise AssertionError(f"coverage index tabs/sessions workflow surface proof parity mismatch: {tabs_sessions_group}")
    tab_action_coverage = request("GET", "/qa/tab-action-coverage")
    if tabs_sessions_group.get("tabActionTabs") != tab_action_coverage.get("tabs"):
        raise AssertionError(f"coverage index tabs/sessions tab action tabs mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionRoutes") != tab_action_coverage.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions tab action route list mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionRouteCount") != len(tab_action_coverage.get("routes") or []):
        raise AssertionError(f"coverage index tabs/sessions tab action route count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionContracts") != tab_action_coverage.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions tab action contract map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionContractCount") != len(tab_action_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions tab action contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionProofs") != tab_action_coverage.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions tab action proof list mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionProofCount") != tab_action_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions tab action proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionStateKeys") != tab_action_coverage.get("actionStateKeys"):
        raise AssertionError(f"coverage index tabs/sessions tab action state-key list mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionStateKeyCount") != len(tab_action_coverage.get("actionStateKeys") or []):
        raise AssertionError(f"coverage index tabs/sessions tab action state-key count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaces") != tab_action_coverage.get("tabActionSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions tab action surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceCount") != tab_action_coverage.get("tabActionSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions tab action surface count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceParity") != tab_action_coverage.get("tabActionSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions tab action surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceProofs") != tab_action_coverage.get("tabActionSurfaceProofs"):
        raise AssertionError(f"coverage index tabs/sessions tab action surface proof map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceProofCount") != tab_action_coverage.get("tabActionSurfaceProofCount"):
        raise AssertionError(f"coverage index tabs/sessions tab action surface proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceProofParity") != tab_action_coverage.get("tabActionSurfaceProofParity"):
        raise AssertionError(f"coverage index tabs/sessions tab action surface proof parity mismatch: {tabs_sessions_group}")

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
