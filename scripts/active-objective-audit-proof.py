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
ROUTE = "/qa/active-objective-audit"

EXPECTED_REQUIREMENTS = [
    "toolFlowUsageBuilt",
    "engineRuntimeBuilt",
    "cacheAndMemoryBuilt",
    "promptInjectionBoundaryBuilt",
    "cveEmbedsDatabaseBuilt",
    "contextCarryMaxTokensCompactionBuilt",
    "stashMemoryBuilt",
    "sessionLifecycleBuilt",
    "parallelSessionsContinuousBatchingBuilt",
    "responsesCacheReuseEndpointBuilt",
    "contentDeltaStreamingBuilt",
    "reasoningAndToolParserBuilt",
    "l2DiskCacheStorageHitBuilt",
    "turboQuantKVCacheComponentBuilt",
    "hybridSSMAsyncReDeriveBuilt",
    "toolLiveStatusLogsBuilt",
    "knownGapBoundaryBuilt",
]

EXPECTED_UPSTREAM_ROWS = {
    "toolFlowUsageBuilt": {"toolFlowUsage"},
    "engineRuntimeBuilt": {"engineRuntime", "localModelLane"},
    "cacheAndMemoryBuilt": {"l2DiskCacheStorageHit", "turboQuantKVCache", "hybridSSMAsyncReDerive"},
    "promptInjectionBoundaryBuilt": {"promptInjectionBoundary"},
    "cveEmbedsDatabaseBuilt": {"cveDatabaseEmbeddings"},
    "contextCarryMaxTokensCompactionBuilt": {"contextCarryCompaction"},
    "stashMemoryBuilt": {"stashMemoryRetrieval"},
    "sessionLifecycleBuilt": {"sessionParallelContinuousBatching"},
    "parallelSessionsContinuousBatchingBuilt": {"sessionParallelContinuousBatching"},
    "responsesCacheReuseEndpointBuilt": {"responsesReuseStreamingParser"},
    "contentDeltaStreamingBuilt": {"responsesReuseStreamingParser"},
    "reasoningAndToolParserBuilt": {"responsesReuseStreamingParser"},
    "l2DiskCacheStorageHitBuilt": {"l2DiskCacheStorageHit"},
    "turboQuantKVCacheComponentBuilt": {"turboQuantKVCache"},
    "hybridSSMAsyncReDeriveBuilt": {"hybridSSMAsyncReDerive"},
    "toolLiveStatusLogsBuilt": {"toolFlowUsage", "proofLedgers"},
    "knownGapBoundaryBuilt": {"knownGapsTracked"},
}


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


def assert_audit(payload: dict, state: dict, index: dict) -> None:
    if payload.get("ok") is not True:
        raise AssertionError(f"{ROUTE} failed: {payload}")
    if payload.get("route") != ROUTE:
        raise AssertionError(f"{ROUTE} route mismatch: {payload}")
    if payload.get("proofLevel") != "explicit-active-objective-requirement-audit":
        raise AssertionError(f"{ROUTE} proof level mismatch: {payload}")
    if payload.get("objectiveComplete") is not False:
        raise AssertionError(f"{ROUTE} must not complete the active objective while gaps remain: {payload}")
    if payload.get("completionClaimAllowed") is not False:
        raise AssertionError(f"{ROUTE} must block completion claims while known gaps remain: {payload}")
    if payload.get("knownGapBoundary") is not True:
        raise AssertionError(f"{ROUTE} missing known-gap boundary: {payload}")
    if payload.get("requirementIds") != EXPECTED_REQUIREMENTS:
        raise AssertionError(f"{ROUTE} requirement order mismatch: {payload}")
    if payload.get("requirementCount") != len(EXPECTED_REQUIREMENTS):
        raise AssertionError(f"{ROUTE} requirement count mismatch: {payload}")
    if payload.get("coveredRequirementCount") != len(EXPECTED_REQUIREMENTS):
        raise AssertionError(f"{ROUTE} should cover every active objective requirement: {payload}")
    if payload.get("routeParity") is not True:
        raise AssertionError(f"{ROUTE} route parity mismatch: {payload}")
    if payload.get("proofFileParity") is not True:
        raise AssertionError(f"{ROUTE} proof-file parity mismatch: {payload}")
    if payload.get("upstreamObjectiveComplete") is not False:
        raise AssertionError(f"{ROUTE} upstream objective completion drift: {payload}")

    rows = {row.get("id"): row for row in payload.get("rows") or []}
    if set(rows) != set(EXPECTED_REQUIREMENTS):
        raise AssertionError(f"{ROUTE} row IDs mismatch: {payload}")
    for requirement in EXPECTED_REQUIREMENTS:
        row = rows.get(requirement) or {}
        if row.get("auditStatus") not in {"covered", "tracked-known-gap"}:
            raise AssertionError(f"{ROUTE} bad audit status for {requirement}: {row}")
        if row.get("coverageStatus") not in {"ready", "tracked-known-gap"}:
            raise AssertionError(f"{ROUTE} bad coverage status for {requirement}: {row}")
        if not row.get("routes"):
            raise AssertionError(f"{ROUTE} row missing routes for {requirement}: {row}")
        if not row.get("proofs"):
            raise AssertionError(f"{ROUTE} row missing proofs for {requirement}: {row}")
        if row.get("routeParity") is not True:
            raise AssertionError(f"{ROUTE} row route parity failed for {requirement}: {row}")
        if row.get("proofFileParity") is not True:
            raise AssertionError(f"{ROUTE} row proof parity failed for {requirement}: {row}")
        upstream_rows = set(row.get("upstreamObjectiveRows") or [])
        if upstream_rows < EXPECTED_UPSTREAM_ROWS[requirement]:
            raise AssertionError(f"{ROUTE} row upstream objective drift for {requirement}: {row}")

    if rows["knownGapBoundaryBuilt"].get("auditStatus") != "tracked-known-gap":
        raise AssertionError(f"{ROUTE} known gap row must be explicit: {rows['knownGapBoundaryBuilt']}")
    if "qwenMultimodalRuntime" not in (payload.get("knownGapIds") or []):
        raise AssertionError(f"{ROUTE} missing Qwen multimodal known gap boundary: {payload}")
    if "response.output_text.delta" not in (rows["contentDeltaStreamingBuilt"].get("streamingEvents") or []):
        raise AssertionError(f"{ROUTE} content delta streaming evidence missing: {rows['contentDeltaStreamingBuilt']}")
    if "response.reasoning.delta" not in (rows["reasoningAndToolParserBuilt"].get("streamingEvents") or []):
        raise AssertionError(f"{ROUTE} reasoning delta evidence missing: {rows['reasoningAndToolParserBuilt']}")
    if "response.function_call_arguments.delta" not in (rows["reasoningAndToolParserBuilt"].get("streamingEvents") or []):
        raise AssertionError(f"{ROUTE} tool-call delta evidence missing: {rows['reasoningAndToolParserBuilt']}")
    if rows["l2DiskCacheStorageHitBuilt"].get("blockL2DiskHits", 0) < 1:
        raise AssertionError(f"{ROUTE} L2 disk hit evidence missing: {rows['l2DiskCacheStorageHitBuilt']}")
    if rows["turboQuantKVCacheComponentBuilt"].get("qwenKVBits") != 4:
        raise AssertionError(f"{ROUTE} Qwen TurboQuant KV evidence missing: {rows['turboQuantKVCacheComponentBuilt']}")
    if rows["turboQuantKVCacheComponentBuilt"].get("minimaxKVBits") != 4:
        raise AssertionError(f"{ROUTE} MiniMax TurboQuant KV evidence missing: {rows['turboQuantKVCacheComponentBuilt']}")
    if rows["hybridSSMAsyncReDeriveBuilt"].get("completed", 0) < 1:
        raise AssertionError(f"{ROUTE} hybrid SSM rederive evidence missing: {rows['hybridSSMAsyncReDeriveBuilt']}")
    if rows["parallelSessionsContinuousBatchingBuilt"].get("qwenMaxRunningObserved", 0) < 4:
        raise AssertionError(f"{ROUTE} Qwen high-cardinality batching evidence missing: {rows['parallelSessionsContinuousBatchingBuilt']}")
    if rows["contextCarryMaxTokensCompactionBuilt"].get("maxPacketChars") != 6000:
        raise AssertionError(f"{ROUTE} context packet budget mismatch: {rows['contextCarryMaxTokensCompactionBuilt']}")
    if rows["contextCarryMaxTokensCompactionBuilt"].get("maxSnippets") != 8:
        raise AssertionError(f"{ROUTE} context snippet cap mismatch: {rows['contextCarryMaxTokensCompactionBuilt']}")
    if rows["cveEmbedsDatabaseBuilt"].get("includeOnlyMode") != "includeOnly-cve-id-allowlist":
        raise AssertionError(f"{ROUTE} CVE include-only mode mismatch: {rows['cveEmbedsDatabaseBuilt']}")

    state_routes = ((state.get("qaCoverage") or {}).get("stateRoutes") or [])
    if ROUTE not in state_routes:
        raise AssertionError(f"/state qaCoverage missing {ROUTE}: {state.get('qaCoverage')}")
    release_group = ((index.get("groups") or {}).get("releaseReadiness") or {})
    if ROUTE not in (release_group.get("endpoints") or []):
        raise AssertionError(f"/qa/coverage-index release group missing {ROUTE}: {release_group}")
    if release_group.get("activeObjectiveAuditRequirementCount") != payload.get("requirementCount"):
        raise AssertionError(f"/qa/coverage-index audit requirement count mismatch: {release_group}")
    if release_group.get("activeObjectiveAuditCoveredRequirementCount") != payload.get("coveredRequirementCount"):
        raise AssertionError(f"/qa/coverage-index audit covered count mismatch: {release_group}")
    if release_group.get("activeObjectiveAuditKnownGapBoundary") != payload.get("knownGapBoundary"):
        raise AssertionError(f"/qa/coverage-index audit known-gap mirror mismatch: {release_group}")
    if release_group.get("activeObjectiveAuditCompletionClaimAllowed") != payload.get("completionClaimAllowed"):
        raise AssertionError(f"/qa/coverage-index audit completion mirror mismatch: {release_group}")
    if release_group.get("activeObjectiveAuditProofFileParity") != payload.get("proofFileParity"):
        raise AssertionError(f"/qa/coverage-index audit proof parity mismatch: {release_group}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        audit = request("GET", ROUTE, timeout=45.0)
        state = request("GET", "/state")
        index = request("GET", "/qa/coverage-index", timeout=45.0)
        assert_audit(audit, state, index)
        print("active-objective-audit proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"active-objective-audit proof failed: {exc}", flush=True)
        raise SystemExit(1)
