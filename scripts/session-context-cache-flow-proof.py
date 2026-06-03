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

EXPECTED_FLOW_ROWS = [
    "newContextCachePreservation",
    "responsesPreviousResponseReuse",
    "boundedContextCompaction",
    "stashAndCVEOnDemandRetrieval",
    "parallelAgentSessions",
    "liveLoadedModelAgentStress",
    "continuousBatchingConcurrency",
    "streamingDeltaParser",
    "runtimeCacheComponents",
    "qwenHybridSSMAsyncReDerive",
]

EXPECTED_CONTRACTS = {
    "sessionWorkflowMatrix",
    "newContextPreservesCache",
    "maxTokenBudgetForwarding",
    "boundedAutomaticContext",
    "stashOnDemandContext",
    "cveOnDemandContext",
    "responsesPreviousResponseReuse",
    "streamingContentDelta",
    "streamingReasoningDelta",
    "streamingToolCallDelta",
    "streamingUsageCachedTokens",
    "parallelAgentProof",
    "liveLoadedModelAgentStress",
    "continuousBatchingProof",
    "qwenLiveContinuousBatchingArtifact",
    "qwenHighCardinalityLiveContinuousBatchingArtifact",
    "minimaxLiveContinuousBatchingArtifact",
    "qwenHybridSSMReDeriveArtifact",
    "turboQuantKVCache",
    "l2DiskCache",
    "blockL2DiskCache",
}


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


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        payload = request("GET", "/qa/session-context-cache-flow")
        if payload.get("ok") is not True:
            raise AssertionError(f"session/context/cache flow route failed: {payload}")
        if payload.get("route") != "/qa/session-context-cache-flow":
            raise AssertionError(f"session/context/cache flow route label mismatch: {payload}")
        if payload.get("proofLevel") != "app-state-and-live-artifact-backed":
            raise AssertionError(f"session/context/cache flow proof level mismatch: {payload}")
        if payload.get("flowRows") != EXPECTED_FLOW_ROWS:
            raise AssertionError(f"session/context/cache flow row order mismatch: {payload}")
        if payload.get("flowRowCount") != len(EXPECTED_FLOW_ROWS):
            raise AssertionError(f"session/context/cache flow row count mismatch: {payload}")
        if payload.get("contextCarryMode") != "bounded-automatic-plus-on-demand-retrieval":
            raise AssertionError(f"context carry mode mismatch: {payload}")
        if payload.get("newContextCacheMode") != "clear-visible-chat-preserve-engine-cache-session":
            raise AssertionError(f"new context cache mode mismatch: {payload}")
        if payload.get("responsesReuseMode") != "store-response-session-and-resolve-previous-response-id":
            raise AssertionError(f"Responses reuse mode mismatch: {payload}")
        if payload.get("liveAgentStressArtifactOK") is not True:
            raise AssertionError(f"live loaded-model agent stress not reflected in session/cache flow: {payload}")
        if payload.get("liveAgentStressAppMaxWorkingObserved", 0) < 2:
            raise AssertionError(f"live agent app concurrency too low in session/cache flow: {payload}")
        if payload.get("liveAgentStressEngineMaxRunningObserved", 0) < 2:
            raise AssertionError(f"live agent engine concurrency too low in session/cache flow: {payload}")
        if payload.get("continuousBatchingProofLevel") != "source-and-live-qwen-minimax-plus-qwen-4way-stress-backed":
            raise AssertionError(f"continuous batching proof level mismatch: {payload}")
        if payload.get("qwenHighCardinalityContinuousBatchingMaxRunningObserved", 0) < 4:
            raise AssertionError(f"Qwen high-cardinality live batching not reflected in session/cache flow: {payload}")
        if payload.get("minimaxContinuousBatchingMaxRunningObserved", 0) < 2:
            raise AssertionError(f"MiniMax live batching not reflected in session/cache flow: {payload}")
        expected_deltas = {"delta.content", "delta.reasoning_content", "delta.tool_calls", "usage.prompt_tokens_details.cached_tokens"}
        if not expected_deltas.issubset(set(payload.get("streamingDeltaSurfaces") or [])):
            raise AssertionError(f"streaming delta surfaces missing: {payload}")
        for component in ("prefixCache", "promptL2Disk", "blockL2Disk", "turboQuantKV", "ssmCompanionL2"):
            if component not in (payload.get("cacheComponents") or []):
                raise AssertionError(f"cache component missing {component}: {payload}")

        contracts = payload.get("contracts") or {}
        missing = sorted(name for name in EXPECTED_CONTRACTS if contracts.get(name) is not True)
        if missing:
            raise AssertionError(f"session/context/cache flow missing contracts {missing}: {payload}")
        if payload.get("contractCount") != len(EXPECTED_CONTRACTS):
            raise AssertionError(f"session/context/cache contract count mismatch: {payload}")
        if payload.get("contractParity") is not True:
            raise AssertionError(f"session/context/cache contract parity mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"session/context/cache proof-file parity mismatch: {payload}")

        state = request("GET", "/state")
        routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/session-context-cache-flow" not in routes:
            raise AssertionError(f"state route list missing session/context/cache route: {routes}")

        deep = request("GET", "/qa/deep-runtime-flow-coverage")
        if "/qa/session-context-cache-flow" not in (deep.get("routes") or []):
            raise AssertionError(f"deep runtime flow missing session/context/cache route: {deep}")
        if deep.get("sessionContextCacheFlowContractParity") is not True:
            raise AssertionError(f"deep runtime flow missing session/context/cache parity: {deep}")

        index = request("GET", "/qa/coverage-index")
        runtime_group = (index.get("groups") or {}).get("runtimeAndCache") or {}
        if "/qa/session-context-cache-flow" not in (runtime_group.get("endpoints") or []):
            raise AssertionError(f"coverage index runtime group missing session/context/cache route: {runtime_group}")
        if runtime_group.get("sessionContextCacheFlowContractParity") is not True:
            raise AssertionError(f"coverage index missing session/context/cache parity: {runtime_group}")

        print("session-context-cache-flow proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"session-context-cache-flow proof failed: {exc}", flush=True)
        raise SystemExit(1)
