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

EXPECTED_CONTRACTS = {
    "serverContinuousBatchingFlag",
    "serverMaxNumSeqsFlag",
    "launcherMaxNumSeqs",
    "serverBatchedEngineSelection",
    "llmWaitingRunningQueues",
    "llmObservedConcurrencyStats",
    "llmPrefixCacheL2",
    "llmTurboQuantKV",
    "mllmSchedulerQueues",
    "mllmObservedConcurrencyStats",
    "mllmBatchGenerator",
    "mllmBatchCacheMerge",
    "mllmAsyncEval",
    "hybridSSMCompanion",
    "hybridMambaBatchCache",
    "mllmContinuousBatchServing",
}

EXPECTED_SOURCE_FILES = {
    "ExploitBotEngine/launch.py",
    "ExploitBotEngine/vmlx_engine/server.py",
    "ExploitBotEngine/vmlx_engine/engine/batched.py",
    "ExploitBotEngine/vmlx_engine/scheduler.py",
    "ExploitBotEngine/vmlx_engine/mllm_scheduler.py",
    "ExploitBotEngine/vmlx_engine/mllm_batch_generator.py",
    "ExploitBotEngine/vmlx_engine/utils/mamba_cache.py",
}

EXPECTED_PROOFS = {
    "continuous-batching-coverage-proof.py",
    "parallel-agent-session-proof.py",
    "runtime-coverage-proof.py",
    "runtime-concurrency-stats-proof.py",
    "runtime-continuous-batching-cli-proof.py",
    "prove-live-continuous-batching.py",
    "prove-live-minimax-continuous-batching.py",
    "minimax-continuous-batching-readiness-proof.py",
}


def request(method: str, path: str, body: str | dict | None = None, timeout: float = 20.0):
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

        state = request("GET", "/state")
        coverage = request("GET", "/qa/continuous-batching-coverage")
        runtime = request("GET", "/qa/runtime-coverage")
        deep = request("GET", "/qa/deep-runtime-flow-coverage")
        index = request("GET", "/qa/coverage-index")

        if coverage.get("ok") is not True:
            raise AssertionError(f"continuous batching route failed: {coverage}")
        if coverage.get("proofLevel") != "source-and-live-qwen-stress-backed":
            raise AssertionError(f"unexpected proof level: {coverage}")
        if coverage.get("liveLoadedModelStress") != "qwen-live-max-running-observed-2":
            raise AssertionError(f"live stress label mismatch: {coverage}")
        if coverage.get("liveLoadedModelStressScope") != "qwen-live-proven-minimax-live-batching-not-run":
            raise AssertionError(f"live stress scope mismatch: {coverage}")
        if coverage.get("qwenContinuousBatchingArtifact") != "docs/live-proofs/checkpoint-452-qwen-continuous-batching-live.json":
            raise AssertionError(f"qwen continuous batching artifact path mismatch: {coverage}")
        if coverage.get("qwenContinuousBatchingArtifactOK") is not True:
            raise AssertionError(f"qwen continuous batching artifact not accepted: {coverage}")
        if coverage.get("qwenContinuousBatchingClientOverlap") is not True:
            raise AssertionError(f"qwen continuous batching did not expose overlap: {coverage}")
        if coverage.get("qwenContinuousBatchingMaxNumSeqs") != 2:
            raise AssertionError(f"qwen continuous batching max-num-seqs mismatch: {coverage}")
        if coverage.get("qwenContinuousBatchingMaxRunningObserved", 0) < 2:
            raise AssertionError(f"qwen continuous batching max running too low: {coverage}")
        if coverage.get("qwenContinuousBatchingMaxWaitingObserved", 0) < 2:
            raise AssertionError(f"qwen continuous batching max waiting too low: {coverage}")
        if coverage.get("qwenContinuousBatchingRequestsProcessed", 0) < 2:
            raise AssertionError(f"qwen continuous batching processed too few requests: {coverage}")
        if coverage.get("qwenContinuousBatchingKVBits") != 4:
            raise AssertionError(f"qwen continuous batching KV bits mismatch: {coverage}")
        if coverage.get("qwenContinuousBatchingBlockL2DiskWrites", 0) < 1:
            raise AssertionError(f"qwen continuous batching missing block L2 writes: {coverage}")
        if coverage.get("qwenContinuousBatchingSSMReDeriveCompleted", 0) < 1:
            raise AssertionError(f"qwen continuous batching missing SSM rederive completions: {coverage}")
        if coverage.get("qwenContinuousBatchingSSMReDeriveFailed") != 0:
            raise AssertionError(f"qwen continuous batching had SSM rederive failures: {coverage}")
        if coverage.get("minimaxContinuousBatchingModel") != "/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ":
            raise AssertionError(f"minimax continuous batching model path mismatch: {coverage}")
        if coverage.get("minimaxContinuousBatchingArtifact") != "docs/live-proofs/checkpoint-464-minimax-continuous-batching-live.json":
            raise AssertionError(f"minimax continuous batching artifact path mismatch: {coverage}")
        if coverage.get("minimaxContinuousBatchingArtifactRequired") is not True:
            raise AssertionError(f"minimax continuous batching artifact should be required: {coverage}")
        if coverage.get("minimaxContinuousBatchingLiveReady") not in {True, False}:
            raise AssertionError(f"minimax continuous batching ready flag missing: {coverage}")
        if not coverage.get("minimaxContinuousBatchingNextCommand"):
            raise AssertionError(f"minimax continuous batching next command missing: {coverage}")

        contracts = coverage.get("contracts") or {}
        missing = sorted(name for name in EXPECTED_CONTRACTS if contracts.get(name) is not True)
        if missing:
            raise AssertionError(f"missing continuous batching contracts {missing}: {coverage}")
        if coverage.get("contractCount") != len(EXPECTED_CONTRACTS):
            raise AssertionError(f"continuous batching contract count mismatch: {coverage}")
        if coverage.get("contractParity") is not True:
            raise AssertionError(f"continuous batching contract parity mismatch: {coverage}")

        source_files = set(coverage.get("sourceFiles") or [])
        if source_files != EXPECTED_SOURCE_FILES:
            raise AssertionError(f"continuous batching source file mismatch: {coverage}")
        if coverage.get("sourceFileCount") != len(EXPECTED_SOURCE_FILES):
            raise AssertionError(f"continuous batching source count mismatch: {coverage}")
        if coverage.get("sourceFileParity") is not True:
            raise AssertionError(f"continuous batching source file parity mismatch: {coverage}")
        missing_source_files = sorted(path for path in EXPECTED_SOURCE_FILES if not (ROOT / path).is_file())
        if missing_source_files:
            raise AssertionError(f"continuous batching source files missing on disk: {missing_source_files}")

        proofs = set(coverage.get("proofs") or [])
        if proofs != EXPECTED_PROOFS:
            raise AssertionError(f"continuous batching proof list mismatch: {coverage}")
        if coverage.get("proofFileParity") is not True:
            raise AssertionError(f"continuous batching proof file parity mismatch: {coverage}")
        missing_proofs = sorted(name for name in EXPECTED_PROOFS if not (ROOT / "scripts" / name).is_file())
        if missing_proofs:
            raise AssertionError(f"continuous batching proof files missing: {missing_proofs}")

        qa_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/continuous-batching-coverage" not in qa_routes:
            raise AssertionError(f"state QA route list missing continuous batching: {qa_routes}")

        runtime_contracts = runtime.get("contracts") or {}
        if runtime_contracts.get("continuousBatchingSource") is not True:
            raise AssertionError(f"runtime coverage missing batching source contract: {runtime}")
        if runtime.get("continuousBatchingContracts") != contracts:
            raise AssertionError(f"runtime coverage batching contract map mismatch: {runtime}")
        if runtime.get("continuousBatchingProofLevel") != coverage.get("proofLevel"):
            raise AssertionError(f"runtime coverage batching proof level mismatch: {runtime}")
        if runtime.get("qwenContinuousBatchingArtifactOK") is not True:
            raise AssertionError(f"runtime coverage missing qwen live batching artifact: {runtime}")
        if runtime.get("qwenContinuousBatchingMaxRunningObserved") != coverage.get("qwenContinuousBatchingMaxRunningObserved"):
            raise AssertionError(f"runtime coverage qwen live batching stats mismatch: {runtime}")

        deep_contracts = deep.get("contracts") or {}
        if deep_contracts.get("continuousBatchingSourceCoverage") is not True:
            raise AssertionError(f"deep runtime missing batching source contract: {deep}")
        if deep_contracts.get("liveQwenContinuousBatching") is not True:
            raise AssertionError(f"deep runtime missing qwen live batching contract: {deep}")
        if "continuousBatching" not in (deep.get("domains") or []):
            raise AssertionError(f"deep runtime missing batching domain: {deep}")
        if "/qa/continuous-batching-coverage" not in (deep.get("routes") or []):
            raise AssertionError(f"deep runtime missing batching route: {deep}")

        runtime_group = (index.get("groups") or {}).get("runtimeAndCache") or {}
        if "/qa/continuous-batching-coverage" not in (runtime_group.get("endpoints") or []):
            raise AssertionError(f"coverage index missing batching endpoint: {runtime_group}")
        if runtime_group.get("continuousBatchingContracts") != contracts:
            raise AssertionError(f"coverage index batching contract map mismatch: {runtime_group}")
        if runtime_group.get("continuousBatchingContractParity") is not True:
            raise AssertionError(f"coverage index batching contract parity mismatch: {runtime_group}")
        if runtime_group.get("continuousBatchingSourceFileParity") is not True:
            raise AssertionError(f"coverage index batching source parity mismatch: {runtime_group}")
        if runtime_group.get("qwenContinuousBatchingArtifactOK") is not True:
            raise AssertionError(f"coverage index missing qwen live batching artifact: {runtime_group}")
        if runtime_group.get("qwenContinuousBatchingMaxRunningObserved") != coverage.get("qwenContinuousBatchingMaxRunningObserved"):
            raise AssertionError(f"coverage index qwen live batching stats mismatch: {runtime_group}")

        print("continuous-batching-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"continuous-batching-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
