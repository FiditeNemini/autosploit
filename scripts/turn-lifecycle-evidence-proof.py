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
ROUTE = "/qa/turn-lifecycle-evidence"

EXPECTED_PHASES = [
    "turnInput",
    "contextBudgetAndCompaction",
    "cveIncludeAndSemanticRetrieval",
    "stashMemoryRetrieval",
    "promptInjectionBoundary",
    "toolSchemaAndLiveStatus",
    "responsesReuseAndStreaming",
    "reasoningAndToolParser",
    "parallelSessionBatching",
    "l2DiskCache",
    "turboQuantKV",
    "hybridSSMAsyncReDerive",
    "resultLogAndKnownGapBoundary",
]

REQUIRED_PROOFS = {
    "turn-lifecycle-evidence-proof.py",
    "per-turn-runtime-contract-proof.py",
    "objective-flow-execution-graph-proof.py",
    "context-budget-compaction-proof.py",
    "cve-import-embedding-coverage-proof.py",
    "stash-retrieval-proof.py",
    "agent-live-tool-status-proof.py",
    "streaming-parser-reuse-proof.py",
    "cache-artifact-matrix-proof.py",
    "continuous-batching-coverage-proof.py",
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


def assert_lifecycle(payload: dict, state: dict, index: dict) -> None:
    if payload.get("ok") is not True:
        raise AssertionError(f"{ROUTE} failed: {payload}")
    if payload.get("route") != ROUTE:
        raise AssertionError(f"{ROUTE} route mismatch: {payload}")
    if payload.get("proofLevel") != "per-turn-objective-lifecycle-route-backed":
        raise AssertionError(f"{ROUTE} proof level mismatch: {payload}")
    if payload.get("phaseIds") != EXPECTED_PHASES:
        raise AssertionError(f"{ROUTE} phase order mismatch: {payload}")
    if payload.get("phaseCount") != len(EXPECTED_PHASES):
        raise AssertionError(f"{ROUTE} phase count mismatch: {payload}")
    if payload.get("readyPhaseCount", 0) < 12:
        raise AssertionError(f"{ROUTE} ready phase count too low: {payload}")
    if payload.get("objectiveComplete") is not False:
        raise AssertionError(f"{ROUTE} must preserve incomplete objective boundary: {payload}")
    if payload.get("knownGapBoundary") is not True:
        raise AssertionError(f"{ROUTE} missing known gap boundary: {payload}")
    if payload.get("contractParity") is not True:
        raise AssertionError(f"{ROUTE} contract parity mismatch: {payload}")
    if payload.get("proofFileParity") is not True:
        raise AssertionError(f"{ROUTE} proof parity mismatch: {payload}")
    if set(payload.get("proofs") or []) < REQUIRED_PROOFS:
        raise AssertionError(f"{ROUTE} missing proofs: {payload}")

    phases = {phase.get("id"): phase for phase in payload.get("phases") or []}
    for phase_id in EXPECTED_PHASES:
        phase = phases.get(phase_id) or {}
        if phase.get("status") != "ready":
            raise AssertionError(f"{ROUTE} phase not ready {phase_id}: {phase}")
        if not phase.get("routes"):
            raise AssertionError(f"{ROUTE} phase missing routes {phase_id}: {phase}")
        if not phase.get("proofs"):
            raise AssertionError(f"{ROUTE} phase missing proofs {phase_id}: {phase}")
        if phase.get("contractOK") is not True:
            raise AssertionError(f"{ROUTE} phase contract failed {phase_id}: {phase}")

    if phases["contextBudgetAndCompaction"].get("maxPacketChars") != 6000:
        raise AssertionError(f"{ROUTE} context budget mismatch: {phases['contextBudgetAndCompaction']}")
    if phases["contextBudgetAndCompaction"].get("maxSnippets") != 8:
        raise AssertionError(f"{ROUTE} context snippet cap mismatch: {phases['contextBudgetAndCompaction']}")
    if phases["cveIncludeAndSemanticRetrieval"].get("includeOnlyMode") != "includeOnly-cve-id-allowlist":
        raise AssertionError(f"{ROUTE} CVE include mode mismatch: {phases['cveIncludeAndSemanticRetrieval']}")
    if phases["toolSchemaAndLiveStatus"].get("schemaCap", 0) > 12:
        raise AssertionError(f"{ROUTE} tool schema cap too high: {phases['toolSchemaAndLiveStatus']}")
    if phases["responsesReuseAndStreaming"].get("responsesReuseMode") != "store-response-session-and-resolve-previous-response-id":
        raise AssertionError(f"{ROUTE} Responses reuse mismatch: {phases['responsesReuseAndStreaming']}")
    required_events = {"response.output_text.delta", "response.reasoning.delta", "response.function_call_arguments.delta"}
    if not required_events.issubset(set(phases["responsesReuseAndStreaming"].get("streamEvents") or [])):
        raise AssertionError(f"{ROUTE} streaming events mismatch: {phases['responsesReuseAndStreaming']}")
    if phases["parallelSessionBatching"].get("qwenMaxRunningObserved", 0) < 4:
        raise AssertionError(f"{ROUTE} Qwen batching evidence missing: {phases['parallelSessionBatching']}")
    if phases["l2DiskCache"].get("blockL2DiskHits", 0) < 1:
        raise AssertionError(f"{ROUTE} block L2 hit evidence missing: {phases['l2DiskCache']}")
    if phases["turboQuantKV"].get("qwenKVBits") != 4 or phases["turboQuantKV"].get("minimaxKVBits") != 4:
        raise AssertionError(f"{ROUTE} TurboQuant q4 evidence missing: {phases['turboQuantKV']}")
    if phases["hybridSSMAsyncReDerive"].get("completed", 0) < 1:
        raise AssertionError(f"{ROUTE} SSM rederive evidence missing: {phases['hybridSSMAsyncReDerive']}")
    if phases["resultLogAndKnownGapBoundary"].get("knownGapCount", 0) < 1:
        raise AssertionError(f"{ROUTE} known gap count missing: {phases['resultLogAndKnownGapBoundary']}")

    state_routes = ((state.get("qaCoverage") or {}).get("stateRoutes") or [])
    if ROUTE not in state_routes:
        raise AssertionError(f"/state qaCoverage route missing {ROUTE}: {state.get('qaCoverage')}")

    runtime_group = ((index.get("groups") or {}).get("runtimeAndCache") or {})
    if ROUTE not in (runtime_group.get("endpoints") or []):
        raise AssertionError(f"/qa/coverage-index runtime group missing {ROUTE}: {runtime_group}")
    if "turn-lifecycle-evidence-proof.py" not in (runtime_group.get("proofs") or []):
        raise AssertionError(f"/qa/coverage-index runtime group missing lifecycle proof: {runtime_group}")
    if runtime_group.get("turnLifecyclePhaseIds") != payload.get("phaseIds"):
        raise AssertionError(f"/qa/coverage-index lifecycle phase mirror mismatch: {runtime_group}")
    if runtime_group.get("turnLifecycleReadyPhaseCount") != payload.get("readyPhaseCount"):
        raise AssertionError(f"/qa/coverage-index lifecycle ready count mismatch: {runtime_group}")
    if runtime_group.get("turnLifecycleKnownGapBoundary") != payload.get("knownGapBoundary"):
        raise AssertionError(f"/qa/coverage-index lifecycle gap boundary mismatch: {runtime_group}")
    if runtime_group.get("turnLifecycleProofFileParity") != payload.get("proofFileParity"):
        raise AssertionError(f"/qa/coverage-index lifecycle proof parity mismatch: {runtime_group}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        lifecycle = request("GET", ROUTE, timeout=45.0)
        state = request("GET", "/state")
        index = request("GET", "/qa/coverage-index", timeout=120.0)
        assert_lifecycle(lifecycle, state, index)
        print("turn-lifecycle-evidence proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"turn-lifecycle-evidence proof failed: {exc}", flush=True)
        raise SystemExit(1)
