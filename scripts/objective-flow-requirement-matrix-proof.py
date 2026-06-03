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
    "toolFlowUsage",
    "engineRuntime",
    "localModelLane",
    "contextCarryCompaction",
    "promptInjectionBoundary",
    "cveDatabaseEmbeddings",
    "stashMemoryRetrieval",
    "sessionParallelContinuousBatching",
    "responsesReuseStreamingParser",
    "l2DiskCacheStorageHit",
    "turboQuantKVCache",
    "hybridSSMAsyncReDerive",
    "proofLedgers",
    "releasePackageReadiness",
    "knownGapsTracked",
]

EXPECTED_EVIDENCE_LEVELS = {
    "toolFlowUsage": "app-route-backed",
    "engineRuntime": "source-and-live-artifact-backed",
    "localModelLane": "release-app-live-artifact-backed",
    "contextCarryCompaction": "app-route-backed",
    "promptInjectionBoundary": "app-route-backed",
    "cveDatabaseEmbeddings": "app-state-and-source-backed",
    "stashMemoryRetrieval": "app-route-backed",
    "sessionParallelContinuousBatching": "live-app-agents-and-engine-backed",
    "responsesReuseStreamingParser": "app-source-and-engine-test-backed",
    "l2DiskCacheStorageHit": "live-artifact-backed",
    "turboQuantKVCache": "live-artifact-backed",
    "hybridSSMAsyncReDerive": "live-artifact-backed",
    "proofLedgers": "ledger-backed",
    "releasePackageReadiness": "package-and-release-ledger-backed",
    "knownGapsTracked": "gap-ledger-backed",
}

REQUIRED_ROW_PROOFS = {
    "toolFlowUsage": {"tool-flow-coverage-proof.py", "tool-registry-coverage-proof.py"},
    "contextCarryCompaction": {"context-budget-compaction-proof.py"},
    "promptInjectionBoundary": {"context-prompt-injection-boundary-proof.py"},
    "cveDatabaseEmbeddings": {"cve-import-embedding-coverage-proof.py", "semantic-cve-proof.py"},
    "stashMemoryRetrieval": {"stash-coverage-proof.py", "stash-retrieval-proof.py"},
    "sessionParallelContinuousBatching": {
        "session-context-cache-flow-proof.py",
        "live-loaded-model-agent-stress-proof.py",
        "prove-live-loaded-model-agent-stress.py",
        "prove-live-continuous-batching.py",
        "prove-live-minimax-continuous-batching.py",
    },
    "responsesReuseStreamingParser": {"streaming-parser-reuse-proof.py", "prove-parser-api.py"},
    "l2DiskCacheStorageHit": {"cache-artifact-matrix-proof.py", "prove-block-l2-cache.py"},
    "turboQuantKVCache": {"runtime-coverage-proof.py", "cache-artifact-matrix-proof.py"},
    "hybridSSMAsyncReDerive": {"runtime-coverage-proof.py", "prove-live-continuous-batching.py"},
}

REQUIRED_LIVE_ARTIFACT_ROWS = {
    "localModelLane",
    "sessionParallelContinuousBatching",
    "l2DiskCacheStorageHit",
    "turboQuantKVCache",
    "hybridSSMAsyncReDerive",
}


def request(method: str, path: str, body: str | None = None, timeout: float = 45.0):
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

        matrix = request("GET", "/qa/objective-flow-requirement-matrix", timeout=35.0)
        objective = request("GET", "/qa/objective-runtime-coverage")
        index = request("GET", "/qa/coverage-index", timeout=45.0)
        state = request("GET", "/state")

        if matrix.get("ok") is not True:
            raise AssertionError(f"objective flow requirement matrix failed: {matrix}")
        if matrix.get("route") != "/qa/objective-flow-requirement-matrix":
            raise AssertionError(f"objective flow requirement route label mismatch: {matrix}")
        if matrix.get("proofLevel") != "requirement-row-route-proof-and-live-artifact-backed":
            raise AssertionError(f"objective flow requirement proof level mismatch: {matrix}")
        if matrix.get("objectiveComplete") is not False:
            raise AssertionError(f"objective flow matrix must preserve known-gap incomplete state: {matrix}")
        if matrix.get("knownGapIds") != objective.get("knownGapIds"):
            raise AssertionError(f"objective flow matrix known gaps drifted from objective route: {matrix}")
        if matrix.get("rowIds") != EXPECTED_ROWS:
            raise AssertionError(f"objective flow matrix row order mismatch: {matrix}")
        if matrix.get("rowCount") != len(EXPECTED_ROWS):
            raise AssertionError(f"objective flow matrix row count mismatch: {matrix}")

        rows = matrix.get("rows") or []
        if len(rows) != len(EXPECTED_ROWS):
            raise AssertionError(f"objective flow matrix rows length mismatch: {matrix}")
        by_id = {row.get("id"): row for row in rows}
        for row_id in EXPECTED_ROWS:
            row = by_id.get(row_id) or {}
            if row.get("id") != row_id:
                raise AssertionError(f"objective flow row missing id {row_id}: {matrix}")
            if row.get("requirement") != row_id:
                raise AssertionError(f"objective flow row requirement mismatch for {row_id}: {row}")
            if row.get("status") not in {"ready", "blocked", "tracked-known-gap"}:
                raise AssertionError(f"objective flow row status mismatch for {row_id}: {row}")
            if row.get("evidenceLevel") != EXPECTED_EVIDENCE_LEVELS[row_id]:
                raise AssertionError(f"objective flow row evidence level mismatch for {row_id}: {row}")
            if row.get("sourceObjectiveRoute") != "/qa/objective-runtime-coverage":
                raise AssertionError(f"objective flow row source route mismatch for {row_id}: {row}")
            if not row.get("routes"):
                raise AssertionError(f"objective flow row missing routes for {row_id}: {row}")
            if not row.get("proofs"):
                raise AssertionError(f"objective flow row missing proofs for {row_id}: {row}")
            if row.get("proofFileParity") is not True:
                raise AssertionError(f"objective flow row proof-file parity mismatch for {row_id}: {row}")
            if row.get("contractParity") is not True:
                raise AssertionError(f"objective flow row contract parity mismatch for {row_id}: {row}")

        for row_id, expected_proofs in REQUIRED_ROW_PROOFS.items():
            proofs = set(by_id[row_id].get("proofs") or [])
            if not expected_proofs.issubset(proofs):
                raise AssertionError(f"objective flow row {row_id} missing proofs {expected_proofs - proofs}: {by_id[row_id]}")

        for row_id in REQUIRED_LIVE_ARTIFACT_ROWS:
            row = by_id[row_id]
            if not row.get("liveArtifacts"):
                raise AssertionError(f"objective flow row {row_id} missing live artifacts: {row}")
            if row.get("liveArtifactParity") is not True:
                raise AssertionError(f"objective flow row {row_id} live artifact parity mismatch: {row}")

        session_row = by_id["sessionParallelContinuousBatching"]
        if "/qa/live-loaded-model-agent-stress" not in (session_row.get("routes") or []):
            raise AssertionError(f"session/parallel row missing loaded-model agent route: {session_row}")
        if "checkpoint-466-qwen-live-agent-stress.json" not in " ".join(session_row.get("liveArtifacts") or []):
            raise AssertionError(f"session/parallel row missing loaded-model agent artifact: {session_row}")

        responses_row = by_id["responsesReuseStreamingParser"]
        required_stream_events = {
            "response.created",
            "response.output_text.delta",
            "response.reasoning.delta",
            "response.function_call_arguments.delta",
            "response.completed",
        }
        if not required_stream_events.issubset(set(responses_row.get("streamingEvents") or [])):
            raise AssertionError(f"responses row missing stream events: {responses_row}")

        objective_evidence = objective.get("evidence") or {}
        for row_id in EXPECTED_ROWS:
            if by_id[row_id].get("status") != (objective_evidence.get(row_id) or {}).get("status"):
                raise AssertionError(f"objective flow row {row_id} status drifted from objective route: {by_id[row_id]}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/objective-flow-requirement-matrix" not in state_routes:
            raise AssertionError(f"state route list missing objective flow matrix: {state_routes}")

        release_group = (index.get("groups") or {}).get("releaseReadiness") or {}
        if "/qa/objective-flow-requirement-matrix" not in (release_group.get("endpoints") or []):
            raise AssertionError(f"coverage index release group missing objective flow matrix: {release_group}")
        if release_group.get("objectiveFlowRequirementRowCount") != len(EXPECTED_ROWS):
            raise AssertionError(f"coverage index objective flow row count mismatch: {release_group}")
        if release_group.get("objectiveFlowRequirementProofFileParity") is not True:
            raise AssertionError(f"coverage index objective flow proof parity mismatch: {release_group}")
        if release_group.get("objectiveFlowRequirementLiveArtifactParity") is not True:
            raise AssertionError(f"coverage index objective flow live artifact parity mismatch: {release_group}")

        print("objective-flow-requirement-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"objective-flow-requirement-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
