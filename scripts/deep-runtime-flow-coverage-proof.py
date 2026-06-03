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

EXPECTED_DOMAINS = [
    "toolRegistry",
    "toolExecution",
    "agentLoop",
    "contextRetrieval",
    "cveTaxonomy",
    "supplyChain",
    "streamingResponses",
    "requestAudit",
    "sessionContextCache",
    "promptInjectionBoundary",
    "localModelLane",
    "sessionWorkflows",
    "parallelAgents",
    "continuousBatching",
    "parserMatrix",
    "runtimeCache",
    "cacheArtifacts",
    "liveCacheArtifacts",
    "stashMemory",
]

EXPECTED_CONTRACTS = {
    "boundedToolSchemas",
    "fullAgentToolSchemas",
    "streamingContentDeltas",
    "streamingReasoningDeltas",
    "streamingToolCallDeltas",
    "responsesEndpointReuse",
    "sessionContextCacheFlow",
    "contextPromptInjectionBoundary",
    "runtimeLocalModelLane",
    "toolParserMatrix",
    "reasoningParserAutodetect",
    "toolParserAutodetect",
    "contextSnippetCap",
    "contextBudgetCompaction",
    "newContextPreservesCacheSession",
    "sessionWorkflowMatrix",
    "parallelAgentLimit",
    "parallelAgentSessionProof",
    "liveLoadedModelAgentStress",
    "continuousBatchingSourceCoverage",
    "cveImportList",
    "cveImportEmbeddingCoverage",
    "semanticCVEEmbeddings",
    "supplyChainTools",
    "cacheResponseReuse",
    "turboQuantKVCache",
    "l2DiskPromptCache",
    "blockL2DiskCache",
    "cacheArtifactMatrix",
    "hybridSSMAsyncReDerive",
    "liveQwenContinuousBatching",
    "liveQwenHighCardinalityContinuousBatching",
    "liveMiniMaxContinuousBatching",
    "liveToolStatusUI",
    "stashRetrievalMemory",
    "promptInjectionBoundedContext",
}

EXPECTED_ROUTES = [
    "/qa/deep-runtime-flow-coverage",
    "/qa/tool-flow-coverage",
    "/qa/tool-execution-matrix",
    "/qa/agent-loop-coverage",
    "/qa/agent-loop-phase-matrix",
    "/qa/session-context-cache-flow",
    "/qa/live-loaded-model-agent-stress",
    "/qa/context-prompt-injection-boundary",
    "/qa/runtime-local-model-lane",
    "/qa/cache-artifact-matrix",
    "/qa/context-coverage",
    "/qa/context-budget-compaction",
    "/qa/context-flow-matrix",
    "/qa/cve-taxonomy-coverage",
    "/qa/cve-taxonomy-matrix",
    "/qa/cve-import-embedding-coverage",
    "/qa/session-coverage",
    "/qa/session-workflow-matrix",
    "/qa/continuous-batching-coverage",
    "/qa/streaming-parser-reuse",
    "/qa/chat-coverage",
    "/qa/parser-tool-matrix",
    "/qa/runtime-coverage",
    "/qa/stash-coverage",
]

EXPECTED_PROOFS = [
    "deep-runtime-flow-coverage-proof.py",
    "session-context-cache-flow-proof.py",
    "live-loaded-model-agent-stress-proof.py",
    "prove-live-loaded-model-agent-stress.py",
    "context-prompt-injection-boundary-proof.py",
    "runtime-local-model-lane-proof.py",
    "cache-artifact-matrix-proof.py",
    "tool-flow-coverage-proof.py",
    "runtime-coverage-proof.py",
    "context-coverage-proof.py",
    "context-budget-compaction-proof.py",
    "cve-taxonomy-coverage-proof.py",
    "cve-import-embedding-coverage-proof.py",
    "session-coverage-proof.py",
    "chat-coverage-proof.py",
    "parser-tool-matrix-proof.py",
    "continuous-batching-coverage-proof.py",
    "streaming-parser-reuse-proof.py",
    "parallel-agent-session-proof.py",
    "runtime-concurrency-stats-proof.py",
    "runtime-continuous-batching-cli-proof.py",
    "prove-live-continuous-batching.py",
    "agent-loop-coverage-proof.py",
    "agent-autopilot-proof.py",
    "supply-chain-cve-ui-proof.py",
    "stash-coverage-proof.py",
]


def request(method: str, path: str, body: str | None = None, timeout: float = 15.0):
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


def assert_file_proofs_exist(proofs: list[str], label: str) -> None:
    missing = [proof for proof in proofs if not (ROOT / "scripts" / proof).is_file()]
    if missing:
        raise AssertionError(f"{label} names missing proof files: {missing}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-result-parser-fixture")
        if seeded.get("ok") is not True:
            raise AssertionError(f"result parser fixture seed failed: {seeded}")

        state = request("GET", "/state")
        coverage = request("GET", "/qa/deep-runtime-flow-coverage")
        index = request("GET", "/qa/coverage-index")
        tool_flow = request("GET", "/qa/tool-flow-coverage")
        runtime = request("GET", "/qa/runtime-coverage")

        if coverage.get("ok") is not True:
            raise AssertionError(f"deep runtime flow coverage route failed: {coverage}")
        if coverage.get("domains") != EXPECTED_DOMAINS:
            raise AssertionError(f"deep runtime flow domain order mismatch: {coverage}")
        if coverage.get("domainCount") != len(EXPECTED_DOMAINS):
            raise AssertionError(f"deep runtime flow domain count mismatch: {coverage}")
        if coverage.get("domainParity") is not True:
            raise AssertionError(f"deep runtime flow domain parity mismatch: {coverage}")
        if coverage.get("domainProofParity") is not True:
            raise AssertionError(f"deep runtime flow domain proof parity mismatch: {coverage}")
        if coverage.get("domainProofFileParity") is not True:
            raise AssertionError(f"deep runtime flow domain proof-file parity mismatch: {coverage}")
        for domain, proofs in (coverage.get("domainProofs") or {}).items():
            assert_file_proofs_exist(proofs, domain)

        contracts = coverage.get("contracts") or {}
        missing_contracts = sorted(name for name in EXPECTED_CONTRACTS if contracts.get(name) is not True)
        if missing_contracts:
            raise AssertionError(f"deep runtime flow missing contracts {missing_contracts}: {coverage}")
        if coverage.get("contractCount") != len(EXPECTED_CONTRACTS):
            raise AssertionError(f"deep runtime flow contract count mismatch: {coverage}")
        if coverage.get("contractParity") is not True:
            raise AssertionError(f"deep runtime flow contract parity mismatch: {coverage}")

        if coverage.get("routes") != EXPECTED_ROUTES:
            raise AssertionError(f"deep runtime flow route list mismatch: {coverage}")
        if coverage.get("routeParity") is not True:
            raise AssertionError(f"deep runtime flow route parity mismatch: {coverage}")
        if coverage.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"deep runtime flow proof list mismatch: {coverage}")
        if coverage.get("proofFileParity") is not True:
            raise AssertionError(f"deep runtime flow proof-file parity mismatch: {coverage}")
        assert_file_proofs_exist(EXPECTED_PROOFS, "deep runtime flow")

        if coverage.get("toolSchemaCap") != 12:
            raise AssertionError(f"bounded per-turn tool schema cap missing: {coverage}")
        if coverage.get("agentToolSchemaMaxTools") != coverage.get("fullToolSchemaCount"):
            raise AssertionError(f"agent full-tool schema contract mismatch: {coverage}")
        if coverage.get("liveAgentStressArtifactOK") is not True:
            raise AssertionError(f"live loaded-model agent stress missing: {coverage}")
        if coverage.get("liveAgentStressAppMaxWorkingObserved", 0) < 2:
            raise AssertionError(f"live loaded-model app concurrency too low: {coverage}")
        if coverage.get("liveAgentStressEngineMaxRunningObserved", 0) < 2:
            raise AssertionError(f"live loaded-model engine concurrency too low: {coverage}")
        if coverage.get("contextSnippetCap") != 4:
            raise AssertionError(f"context cap mismatch: {coverage}")
        if not 1 <= coverage.get("currentInjectedContextLimit", 0) <= 4:
            raise AssertionError(f"current context limit is not bounded: {coverage}")
        if coverage.get("contextBudgetContractParity") is not True:
            raise AssertionError(f"context budget contract parity mismatch: {coverage}")
        if coverage.get("contextBudgetProofFileParity") is not True:
            raise AssertionError(f"context budget proof-file parity mismatch: {coverage}")
        if coverage.get("contextBudgetCompactionFormat") != "single-line-snippet":
            raise AssertionError(f"context budget compaction format mismatch: {coverage}")
        if coverage.get("contextBudgetPromptInjectionPolicy") != "search-on-demand-not-force-injected":
            raise AssertionError(f"context budget prompt-injection policy mismatch: {coverage}")
        if coverage.get("sessionContextCacheFlowContractParity") is not True:
            raise AssertionError(f"session/context/cache flow parity mismatch: {coverage}")
        if coverage.get("sessionContextCacheResponsesReuseMode") != "store-response-session-and-resolve-previous-response-id":
            raise AssertionError(f"session/context/cache Responses reuse mismatch: {coverage}")
        if coverage.get("contextPromptInjectionBoundaryContractParity") is not True:
            raise AssertionError(f"context prompt-injection boundary parity mismatch: {coverage}")
        if coverage.get("contextPromptInjectionBoundaryProofFileParity") is not True:
            raise AssertionError(f"context prompt-injection boundary proof parity mismatch: {coverage}")
        if coverage.get("contextPromptInjectionBoundaryPolicy") != "search-on-demand-not-force-injected":
            raise AssertionError(f"context prompt-injection boundary policy mismatch: {coverage}")
        if coverage.get("runtimeLocalModelLaneContractParity") is not True:
            raise AssertionError(f"runtime local model lane parity mismatch: {coverage}")
        if coverage.get("runtimeLocalModelLaneArtifactFileParity") is not True:
            raise AssertionError(f"runtime local model lane artifact parity mismatch: {coverage}")
        if coverage.get("runtimeLocalModelLaneQwenTargetPath") != "/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP":
            raise AssertionError(f"runtime local model lane Qwen target mismatch: {coverage}")
        if coverage.get("cacheArtifactMatrixContractParity") is not True:
            raise AssertionError(f"cache artifact matrix parity mismatch: {coverage}")
        if coverage.get("cacheArtifactMatrixArtifactFileParity") is not True:
            raise AssertionError(f"cache artifact matrix artifact parity mismatch: {coverage}")
        if coverage.get("cacheArtifactMatrixProofFileParity") is not True:
            raise AssertionError(f"cache artifact matrix proof parity mismatch: {coverage}")
        if coverage.get("cveImportEmbeddingProofFileParity") is not True:
            raise AssertionError(f"CVE import embedding proof parity mismatch: {coverage}")
        if coverage.get("cveImportEmbeddingSourceFileParity") is not True:
            raise AssertionError(f"CVE import embedding source parity mismatch: {coverage}")
        if coverage.get("continuousBatchingProofLevel") != "source-and-live-qwen-minimax-plus-qwen-4way-stress-backed":
            raise AssertionError(f"continuous batching proof level mismatch: {coverage}")
        if coverage.get("continuousBatchingLiveLoadedModelStress") != "qwen-live-max-running-observed-2-minimax-live-max-running-observed-2-qwen4-live-max-running-observed-4":
            raise AssertionError(f"continuous batching live stress label mismatch: {coverage}")
        if coverage.get("continuousBatchingContractParity") is not True:
            raise AssertionError(f"continuous batching contract parity mismatch: {coverage}")
        if coverage.get("streamingParserProofLevel") != "app-source-and-engine-test-backed":
            raise AssertionError(f"streaming parser proof level mismatch: {coverage}")
        if coverage.get("streamingParserContractParity") is not True:
            raise AssertionError(f"streaming parser contract parity mismatch: {coverage}")
        if coverage.get("streamingParserProofFileParity") is not True:
            raise AssertionError(f"streaming parser proof-file parity mismatch: {coverage}")
        if coverage.get("streamingParserResponsesStoreSessionMode") != "store-response-session-and-resolve-previous-response-id":
            raise AssertionError(f"streaming parser session mode mismatch: {coverage}")
        if coverage.get("cacheResponseMethod") != "prefix-cache-l2-turboquant":
            raise AssertionError(f"cache response method mismatch: {coverage}")
        for component in ("prefixCache", "promptL2Disk", "pagedKVCache", "blockL2Disk", "turboQuantKV", "ssmCompanionL2"):
            if component not in (coverage.get("cacheComponents") or []):
                raise AssertionError(f"cache component missing {component}: {coverage}")
        if coverage.get("cacheComponentProofFileParity") is not True:
            raise AssertionError(f"cache component proof-file parity mismatch: {coverage}")
        if coverage.get("liveProofArtifactFileParity") is not True:
            raise AssertionError(f"live proof artifact file parity mismatch: {coverage}")
        for key in ("qwenSSMReDeriveArtifactOK", "qwenSSMReDeriveRequested", "qwenSSMReDeriveCompleted", "qwenSSMReDeriveNoFailures"):
            if coverage.get(key) is not True:
                raise AssertionError(f"Qwen SSM rederive flag missing {key}: {coverage}")
        if coverage.get("qwenContinuousBatchingArtifactOK") is not True:
            raise AssertionError(f"Qwen continuous batching artifact flag missing: {coverage}")
        if coverage.get("qwenContinuousBatchingMaxRunningObserved", 0) < 2:
            raise AssertionError(f"Qwen continuous batching max running too low: {coverage}")
        if coverage.get("qwenContinuousBatchingRequestsProcessed", 0) < 2:
            raise AssertionError(f"Qwen continuous batching request count too low: {coverage}")
        if coverage.get("qwenContinuousBatchingKVBits") != 4:
            raise AssertionError(f"Qwen continuous batching KV bits mismatch: {coverage}")
        if coverage.get("stashSurfaceCount", 0) < 6:
            raise AssertionError(f"stash surface coverage too low: {coverage}")

        qa_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/deep-runtime-flow-coverage" not in qa_routes:
            raise AssertionError(f"state routes missing deep runtime flow route: {qa_routes}")

        runtime_group = (index.get("groups") or {}).get("runtimeAndCache") or {}
        if "/qa/deep-runtime-flow-coverage" not in (runtime_group.get("endpoints") or []):
            raise AssertionError(f"coverage index runtime group missing deep route: {runtime_group}")
        if "/qa/session-context-cache-flow" not in (runtime_group.get("endpoints") or []):
            raise AssertionError(f"coverage index runtime group missing session/context/cache route: {runtime_group}")
        if "/qa/cache-artifact-matrix" not in (runtime_group.get("endpoints") or []):
            raise AssertionError(f"coverage index runtime group missing cache artifact route: {runtime_group}")
        if "/qa/continuous-batching-coverage" not in (runtime_group.get("endpoints") or []):
            raise AssertionError(f"coverage index runtime group missing continuous batching route: {runtime_group}")
        if "/qa/streaming-parser-reuse" not in (runtime_group.get("endpoints") or []):
            raise AssertionError(f"coverage index runtime group missing streaming parser route: {runtime_group}")
        if runtime_group.get("deepRuntimeFlowDomainCount") != coverage.get("domainCount"):
            raise AssertionError(f"coverage index deep domain count mismatch: {runtime_group}")
        if runtime_group.get("deepRuntimeFlowContractParity") != coverage.get("contractParity"):
            raise AssertionError(f"coverage index deep contract parity mismatch: {runtime_group}")
        if runtime_group.get("continuousBatchingContractParity") is not True:
            raise AssertionError(f"coverage index batching contract parity mismatch: {runtime_group}")
        if runtime_group.get("streamingParserContractParity") is not True:
            raise AssertionError(f"coverage index streaming parser contract parity mismatch: {runtime_group}")

        tools_group = (index.get("groups") or {}).get("toolsAndParsers") or {}
        if tools_group.get("toolFlowDomainCount") != tool_flow.get("flowDomainCount"):
            raise AssertionError(f"coverage index tool flow domain count mismatch: {tools_group}")
        if tools_group.get("toolFlowDomainProofFileParity") != tool_flow.get("flowDomainProofFileParity"):
            raise AssertionError(f"coverage index tool flow domain proof parity mismatch: {tools_group}")
        if runtime.get("qwenSSMReDeriveArtifactOK") is not True:
            raise AssertionError(f"runtime route no longer backs Qwen SSM rederive: {runtime}")
        if runtime.get("qwenContinuousBatchingArtifactOK") is not True:
            raise AssertionError(f"runtime route no longer backs Qwen continuous batching: {runtime}")

        print("deep-runtime-flow-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"deep-runtime-flow-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
