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
ROUTE = "/qa/context-efficiency-invariants"

EXPECTED_INVARIANTS = [
    "automaticContextCap",
    "contextPacketBudget",
    "maxTokenAndIterationForwarding",
    "newContextPreservesCache",
    "stashAndCVEOnDemandRetrieval",
    "promptInjectionBoundedContext",
    "responsesPreviousResponseReuse",
    "streamingDeltaCoverage",
    "parallelSessionBatching",
    "qwenMemoryCeiling",
    "l2DiskCacheHit",
    "turboQuantKVQ4",
    "hybridSSMAsyncReDerive",
]


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


def assert_invariants(payload: dict, state: dict, index: dict) -> None:
    if payload.get("ok") is not True:
        raise AssertionError(f"{ROUTE} failed: {payload}")
    if payload.get("route") != ROUTE:
        raise AssertionError(f"{ROUTE} route mismatch: {payload}")
    if payload.get("proofLevel") != "hard-context-session-cache-efficiency-invariants":
        raise AssertionError(f"{ROUTE} proof level mismatch: {payload}")
    if payload.get("invariantIds") != EXPECTED_INVARIANTS:
        raise AssertionError(f"{ROUTE} invariant order mismatch: {payload}")
    if payload.get("invariantCount") != len(EXPECTED_INVARIANTS):
        raise AssertionError(f"{ROUTE} invariant count mismatch: {payload}")
    if payload.get("readyInvariantCount") != len(EXPECTED_INVARIANTS):
        raise AssertionError(f"{ROUTE} should have every invariant ready: {payload}")
    if payload.get("blockedInvariantIds"):
        raise AssertionError(f"{ROUTE} should not have blocked invariants: {payload}")
    if payload.get("contractParity") is not True:
        raise AssertionError(f"{ROUTE} contract parity mismatch: {payload}")
    if payload.get("routeParity") is not True:
        raise AssertionError(f"{ROUTE} route parity mismatch: {payload}")
    if payload.get("proofFileParity") is not True:
        raise AssertionError(f"{ROUTE} proof parity mismatch: {payload}")

    rows = {row.get("id"): row for row in payload.get("rows") or []}
    if set(rows) != set(EXPECTED_INVARIANTS):
        raise AssertionError(f"{ROUTE} row IDs mismatch: {payload}")
    for invariant_id in EXPECTED_INVARIANTS:
        row = rows.get(invariant_id) or {}
        if row.get("status") != "ready":
            raise AssertionError(f"{ROUTE} invariant not ready {invariant_id}: {row}")
        if row.get("contractOK") is not True:
            raise AssertionError(f"{ROUTE} invariant contract failed {invariant_id}: {row}")
        if row.get("routeParity") is not True:
            raise AssertionError(f"{ROUTE} invariant route parity failed {invariant_id}: {row}")
        if row.get("proofFileParity") is not True:
            raise AssertionError(f"{ROUTE} invariant proof parity failed {invariant_id}: {row}")

    if rows["automaticContextCap"].get("automaticInjectedContextCap") != 4:
        raise AssertionError(f"{ROUTE} automatic context cap mismatch: {rows['automaticContextCap']}")
    if rows["contextPacketBudget"].get("maxPacketChars") != 6000:
        raise AssertionError(f"{ROUTE} packet char budget mismatch: {rows['contextPacketBudget']}")
    if rows["contextPacketBudget"].get("maxSnippets") != 8:
        raise AssertionError(f"{ROUTE} packet snippet budget mismatch: {rows['contextPacketBudget']}")
    if rows["maxTokenAndIterationForwarding"].get("engineMaxTokens") != rows["maxTokenAndIterationForwarding"].get("chatMaxTokens"):
        raise AssertionError(f"{ROUTE} max-token forwarding mismatch: {rows['maxTokenAndIterationForwarding']}")
    if rows["newContextPreservesCache"].get("newContextBehavior") != "clear-visible-chat-preserve-engine-cache-session":
        raise AssertionError(f"{ROUTE} new-context cache behavior mismatch: {rows['newContextPreservesCache']}")
    retrieval_sources = set(rows["stashAndCVEOnDemandRetrieval"].get("retrievalSources") or [])
    if not {"stash.note", "cve"}.issubset(retrieval_sources):
        raise AssertionError(f"{ROUTE} retrieval source mismatch: {rows['stashAndCVEOnDemandRetrieval']}")
    if rows["promptInjectionBoundedContext"].get("policy") != "search-on-demand-not-force-injected":
        raise AssertionError(f"{ROUTE} prompt-injection policy mismatch: {rows['promptInjectionBoundedContext']}")
    if rows["responsesPreviousResponseReuse"].get("reuseMode") != "store-response-session-and-resolve-previous-response-id":
        raise AssertionError(f"{ROUTE} Responses reuse mismatch: {rows['responsesPreviousResponseReuse']}")
    required_events = {"response.output_text.delta", "response.reasoning.delta", "response.function_call_arguments.delta"}
    if not required_events.issubset(set(rows["streamingDeltaCoverage"].get("responsesEvents") or [])):
        raise AssertionError(f"{ROUTE} streaming events mismatch: {rows['streamingDeltaCoverage']}")
    if rows["parallelSessionBatching"].get("qwenMaxRunningObserved", 0) < 4:
        raise AssertionError(f"{ROUTE} Qwen batching evidence missing: {rows['parallelSessionBatching']}")
    if rows["parallelSessionBatching"].get("minimaxMaxRunningObserved", 0) < 2:
        raise AssertionError(f"{ROUTE} MiniMax batching evidence missing: {rows['parallelSessionBatching']}")
    if rows["qwenMemoryCeiling"].get("activeMemoryMB", 999999) >= 20000:
        raise AssertionError(f"{ROUTE} Qwen memory ceiling exceeded: {rows['qwenMemoryCeiling']}")
    if rows["l2DiskCacheHit"].get("blockL2DiskHits", 0) < 1:
        raise AssertionError(f"{ROUTE} L2 disk hit missing: {rows['l2DiskCacheHit']}")
    if rows["turboQuantKVQ4"].get("qwenKVBits") != 4 or rows["turboQuantKVQ4"].get("minimaxKVBits") != 4:
        raise AssertionError(f"{ROUTE} TurboQuant q4 mismatch: {rows['turboQuantKVQ4']}")
    if rows["hybridSSMAsyncReDerive"].get("completed", 0) < 1 or rows["hybridSSMAsyncReDerive"].get("failed", 1) != 0:
        raise AssertionError(f"{ROUTE} SSM rederive mismatch: {rows['hybridSSMAsyncReDerive']}")

    state_routes = ((state.get("qaCoverage") or {}).get("stateRoutes") or [])
    if ROUTE not in state_routes:
        raise AssertionError(f"/state qaCoverage missing {ROUTE}: {state.get('qaCoverage')}")
    context_group = ((index.get("groups") or {}).get("chatAndContext") or {})
    runtime_group = ((index.get("groups") or {}).get("runtimeAndCache") or {})
    if ROUTE not in (context_group.get("endpoints") or []):
        raise AssertionError(f"/qa/coverage-index context group missing {ROUTE}: {context_group}")
    if ROUTE not in (runtime_group.get("endpoints") or []):
        raise AssertionError(f"/qa/coverage-index runtime group missing {ROUTE}: {runtime_group}")
    if context_group.get("contextEfficiencyInvariantIds") != payload.get("invariantIds"):
        raise AssertionError(f"/qa/coverage-index context invariant IDs mismatch: {context_group}")
    if runtime_group.get("contextEfficiencyReadyInvariantCount") != payload.get("readyInvariantCount"):
        raise AssertionError(f"/qa/coverage-index runtime ready invariant count mismatch: {runtime_group}")
    if context_group.get("contextEfficiencyContractParity") != payload.get("contractParity"):
        raise AssertionError(f"/qa/coverage-index context contract parity mismatch: {context_group}")
    if runtime_group.get("contextEfficiencyProofFileParity") != payload.get("proofFileParity"):
        raise AssertionError(f"/qa/coverage-index runtime proof parity mismatch: {runtime_group}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        invariants = request("GET", ROUTE, timeout=45.0)
        state = request("GET", "/state")
        index = request("GET", "/qa/coverage-index", timeout=45.0)
        assert_invariants(invariants, state, index)
        print("context-efficiency-invariants proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"context-efficiency-invariants proof failed: {exc}", flush=True)
        raise SystemExit(1)
