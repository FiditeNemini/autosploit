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

EXPECTED_ROWS = [
    "automaticContextCap",
    "maxTokenForwarding",
    "maxIterationBudget",
    "compactionFormat",
    "newContextCachePreservation",
    "stashCVEOnDemand",
    "responsesPreviousResponseReuse",
    "streamingDeltaUsageTelemetry",
    "parallelSessionConcurrency",
    "qwenContinuousBatching",
    "minimaxContinuousBatching",
    "liveLoadedModelAgentStress",
    "l2DiskHitStorage",
    "turboQuantKV",
    "hybridSSMAsyncReDerive",
]

REQUIRED_PROOFS = {
    "context-session-efficiency-matrix-proof.py",
    "context-budget-compaction-proof.py",
    "session-context-cache-flow-proof.py",
    "streaming-parser-reuse-proof.py",
    "cache-artifact-matrix-proof.py",
    "continuous-batching-coverage-proof.py",
    "live-loaded-model-agent-stress-proof.py",
}


def request(method: str, path: str, body: str | None = None, timeout: float = 20.0):
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

        matrix = request("GET", "/qa/context-session-efficiency-matrix", timeout=35.0)
        budget = request("GET", "/qa/context-budget-compaction")
        session = request("GET", "/qa/session-context-cache-flow")
        streaming = request("GET", "/qa/streaming-parser-reuse")
        cache = request("GET", "/qa/cache-artifact-matrix")
        batching = request("GET", "/qa/continuous-batching-coverage")
        live_agent = request("GET", "/qa/live-loaded-model-agent-stress")
        index = request("GET", "/qa/coverage-index", timeout=45.0)
        state = request("GET", "/state")

        if matrix.get("ok") is not True:
            raise AssertionError(f"context/session efficiency matrix failed: {matrix}")
        if matrix.get("route") != "/qa/context-session-efficiency-matrix":
            raise AssertionError(f"context/session efficiency route label mismatch: {matrix}")
        if matrix.get("proofLevel") != "context-session-cache-counter-backed":
            raise AssertionError(f"context/session efficiency proof level mismatch: {matrix}")
        if matrix.get("rowIds") != EXPECTED_ROWS:
            raise AssertionError(f"context/session efficiency row order mismatch: {matrix}")
        if matrix.get("rowCount") != len(EXPECTED_ROWS):
            raise AssertionError(f"context/session efficiency row count mismatch: {matrix}")
        if matrix.get("readyRowCount") != len(EXPECTED_ROWS):
            raise AssertionError(f"context/session efficiency ready row count mismatch: {matrix}")
        if matrix.get("contractParity") is not True:
            raise AssertionError(f"context/session efficiency contract parity mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"context/session efficiency proof-file parity mismatch: {matrix}")

        rows = {row.get("id"): row for row in matrix.get("rows") or []}
        for row_id in EXPECTED_ROWS:
            row = rows.get(row_id) or {}
            if row.get("status") != "ready":
                raise AssertionError(f"context/session efficiency row not ready {row_id}: {row}")
            if row.get("contractOK") is not True:
                raise AssertionError(f"context/session efficiency row contract failed {row_id}: {row}")
            if row.get("proofFileParity") is not True:
                raise AssertionError(f"context/session efficiency row proof parity failed {row_id}: {row}")
            if not row.get("route"):
                raise AssertionError(f"context/session efficiency row missing route {row_id}: {row}")
            if not row.get("proofs"):
                raise AssertionError(f"context/session efficiency row missing proofs {row_id}: {row}")

        if rows["automaticContextCap"].get("limit") != 4:
            raise AssertionError(f"automatic context cap mismatch: {rows['automaticContextCap']}")
        if rows["maxTokenForwarding"].get("maxTokens") != budget.get("maxTokens"):
            raise AssertionError(f"max token row drifted from budget route: {rows['maxTokenForwarding']}")
        if rows["maxIterationBudget"].get("maxIterations") != budget.get("maxIterations"):
            raise AssertionError(f"max iteration row drifted from budget route: {rows['maxIterationBudget']}")
        if rows["compactionFormat"].get("format") != "single-line-snippet":
            raise AssertionError(f"compaction row format mismatch: {rows['compactionFormat']}")
        if rows["newContextCachePreservation"].get("mode") != "clear-visible-chat-preserve-engine-cache-session":
            raise AssertionError(f"new-context cache row mismatch: {rows['newContextCachePreservation']}")
        if rows["stashCVEOnDemand"].get("sources") != ["stash.note", "cve"]:
            raise AssertionError(f"stash/CVE source row mismatch: {rows['stashCVEOnDemand']}")
        if rows["responsesPreviousResponseReuse"].get("mode") != streaming.get("responsesStoreSessionMode"):
            raise AssertionError(f"Responses reuse row drift: {rows['responsesPreviousResponseReuse']}")
        if rows["streamingDeltaUsageTelemetry"].get("usageTelemetry") != streaming.get("usageTelemetry"):
            raise AssertionError(f"streaming usage row drift: {rows['streamingDeltaUsageTelemetry']}")
        if rows["parallelSessionConcurrency"].get("maxConcurrentAgents", 0) < 1:
            raise AssertionError(f"parallel session row missing concurrency: {rows['parallelSessionConcurrency']}")
        if rows["qwenContinuousBatching"].get("maxRunningObserved", 0) < 4:
            raise AssertionError(f"Qwen batching row missing 4-way stress: {rows['qwenContinuousBatching']}")
        if rows["minimaxContinuousBatching"].get("maxRunningObserved", 0) < 2:
            raise AssertionError(f"MiniMax batching row missing live concurrency: {rows['minimaxContinuousBatching']}")
        if rows["liveLoadedModelAgentStress"].get("appMaxWorkingObserved", 0) < 2:
            raise AssertionError(f"live loaded agent row missing app concurrency: {rows['liveLoadedModelAgentStress']}")
        if rows["l2DiskHitStorage"].get("diskHits", 0) < 1 or rows["l2DiskHitStorage"].get("diskWrites", 0) < 1:
            raise AssertionError(f"L2 disk row missing hit/write counters: {rows['l2DiskHitStorage']}")
        if rows["turboQuantKV"].get("qwenKVBits") != 4 or rows["turboQuantKV"].get("minimaxKVBits") != 4:
            raise AssertionError(f"TurboQuant row missing q4 evidence: {rows['turboQuantKV']}")
        if rows["hybridSSMAsyncReDerive"].get("completed", 0) < 1 or rows["hybridSSMAsyncReDerive"].get("failed", 1) != 0:
            raise AssertionError(f"SSM rederive row missing success counters: {rows['hybridSSMAsyncReDerive']}")

        if matrix.get("maxTokens") != session.get("maxTokens"):
            raise AssertionError(f"matrix maxTokens drifted from session route: {matrix}")
        if matrix.get("responsesReuseMode") != session.get("responsesReuseMode"):
            raise AssertionError(f"matrix responses reuse drifted from session route: {matrix}")
        if matrix.get("cacheArtifactContractParity") != cache.get("contractParity"):
            raise AssertionError(f"matrix cache artifact parity drifted: {matrix}")
        if matrix.get("continuousBatchingContractParity") != batching.get("contractParity"):
            raise AssertionError(f"matrix batching parity drifted: {matrix}")
        if matrix.get("liveAgentStressArtifactOK") != live_agent.get("artifactOK"):
            raise AssertionError(f"matrix live agent parity drifted: {matrix}")

        proofs = set(matrix.get("proofs") or [])
        missing_proofs = sorted(REQUIRED_PROOFS.difference(proofs))
        if missing_proofs:
            raise AssertionError(f"context/session efficiency matrix missing proofs {missing_proofs}: {matrix}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/context-session-efficiency-matrix" not in state_routes:
            raise AssertionError(f"state route list missing context/session efficiency matrix: {state_routes}")

        chat_group = (index.get("groups") or {}).get("chatAndContext") or {}
        if "/qa/context-session-efficiency-matrix" not in (chat_group.get("endpoints") or []):
            raise AssertionError(f"coverage index missing context/session efficiency route: {chat_group}")
        if chat_group.get("contextSessionEfficiencyRowCount") != len(EXPECTED_ROWS):
            raise AssertionError(f"coverage index context/session efficiency row count mismatch: {chat_group}")
        if chat_group.get("contextSessionEfficiencyContractParity") is not True:
            raise AssertionError(f"coverage index context/session efficiency contract parity mismatch: {chat_group}")
        if chat_group.get("contextSessionEfficiencyProofFileParity") is not True:
            raise AssertionError(f"coverage index context/session efficiency proof parity mismatch: {chat_group}")

        print("context-session-efficiency-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"context-session-efficiency-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
