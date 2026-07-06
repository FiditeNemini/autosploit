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
ROUTE = "/qa/chat-quality-evidence-matrix"

REQUIRED_ROWS = {
    "qwenReleaseChat",
    "qwenBlockL2SSMReplay",
    "minimaxReleaseChat",
    "minimaxBatchingChat",
    "qualityGapBoundary",
}

REQUIRED_PROOFS = {
    "chat-quality-evidence-matrix-proof.py",
    "release-app-live-qwen-proof.py",
    "release-app-live-minimax-proof.py",
    "verify-live-models.py",
    "runtime-local-model-lane-proof.py",
    "cache-artifact-matrix-proof.py",
    "beta-readiness-coverage-proof.py",
}

REQUIRED_GAPS = {
    "minimaxFirstTurnInstructionFollowing",
    "broadReasoningToolCallQuality",
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


def assert_matrix(matrix: dict, state: dict, coverage_index: dict) -> None:
    if matrix.get("ok") is not True:
        raise AssertionError(f"{ROUTE} failed: {matrix}")
    if matrix.get("route") != ROUTE:
        raise AssertionError(f"{ROUTE} route mismatch: {matrix}")
    if matrix.get("proofLevel") != "live-artifact-quality-evidence-backed":
        raise AssertionError(f"{ROUTE} proof level mismatch: {matrix}")
    if set(matrix.get("rows") or []) != REQUIRED_ROWS:
        raise AssertionError(f"{ROUTE} rows mismatch: {matrix}")
    if matrix.get("rowCount") != len(REQUIRED_ROWS):
        raise AssertionError(f"{ROUTE} row count mismatch: {matrix}")
    if matrix.get("readyRowCount", 0) < 3:
        raise AssertionError(f"{ROUTE} ready rows too low: {matrix}")
    if matrix.get("partialRowCount", 0) < 1:
        raise AssertionError(f"{ROUTE} partial rows too low: {matrix}")
    if matrix.get("broadQualityComplete") is not False:
        raise AssertionError(f"{ROUTE} overclaims broad quality: {matrix}")
    if set(matrix.get("families") or []) != {"qwen", "minimax"}:
        raise AssertionError(f"{ROUTE} family set mismatch: {matrix}")
    if set(matrix.get("knownQualityGaps") or []) < REQUIRED_GAPS:
        raise AssertionError(f"{ROUTE} missing known gaps: {matrix}")
    if matrix.get("artifactFileParity") is not True:
        raise AssertionError(f"{ROUTE} artifact parity mismatch: {matrix}")
    if matrix.get("proofFileParity") is not True:
        raise AssertionError(f"{ROUTE} proof parity mismatch: {matrix}")
    if set(matrix.get("proofs") or []) < REQUIRED_PROOFS:
        raise AssertionError(f"{ROUTE} proofs mismatch: {matrix}")

    row_details = {row.get("id"): row for row in matrix.get("rowDetails") or []}
    qwen_release = row_details.get("qwenReleaseChat") or {}
    if qwen_release.get("status") != "ready" or qwen_release.get("firstResponseNonEmpty") is not True:
        raise AssertionError(f"{ROUTE} qwen release row mismatch: {matrix}")
    if qwen_release.get("cacheReuseEvidence") is not True or qwen_release.get("turboQuantKV") is not True:
        raise AssertionError(f"{ROUTE} qwen cache evidence mismatch: {matrix}")

    qwen_ssm = row_details.get("qwenBlockL2SSMReplay") or {}
    if qwen_ssm.get("status") != "ready" or qwen_ssm.get("ssmAsyncReDerive") is not True:
        raise AssertionError(f"{ROUTE} qwen SSM row mismatch: {matrix}")

    minimax_release = row_details.get("minimaxReleaseChat") or {}
    if minimax_release.get("status") != "partial":
        raise AssertionError(f"{ROUTE} minimax release should remain partial: {matrix}")
    if minimax_release.get("firstResponseNonEmpty") is not True or minimax_release.get("cacheReuseEvidence") is not True:
        raise AssertionError(f"{ROUTE} minimax release evidence mismatch: {matrix}")
    if "minimaxFirstTurnInstructionFollowing" not in minimax_release.get("qualityGaps", []):
        raise AssertionError(f"{ROUTE} minimax quality gap missing: {matrix}")

    minimax_batching = row_details.get("minimaxBatchingChat") or {}
    if minimax_batching.get("status") != "ready" or minimax_batching.get("continuousBatching") is not True:
        raise AssertionError(f"{ROUTE} minimax batching row mismatch: {matrix}")

    state_routes = ((state.get("qaCoverage") or {}).get("stateRoutes") or [])
    if ROUTE not in state_routes:
        raise AssertionError(f"/state qaCoverage route missing {ROUTE}: {state.get('qaCoverage')}")

    runtime_group = ((coverage_index.get("groups") or {}).get("runtimeAndCache") or {})
    if ROUTE not in (runtime_group.get("endpoints") or []):
        raise AssertionError(f"/qa/coverage-index runtime group missing {ROUTE}: {coverage_index}")
    if "chat-quality-evidence-matrix-proof.py" not in (runtime_group.get("proofs") or []):
        raise AssertionError(f"/qa/coverage-index runtime proofs missing chat quality proof: {coverage_index}")
    if runtime_group.get("chatQualityRows") != matrix.get("rows"):
        raise AssertionError(f"/qa/coverage-index chat rows mismatch: {coverage_index}")
    if runtime_group.get("chatQualityReadyRowCount") != matrix.get("readyRowCount"):
        raise AssertionError(f"/qa/coverage-index chat ready row mismatch: {coverage_index}")
    if runtime_group.get("chatQualityPartialRowCount") != matrix.get("partialRowCount"):
        raise AssertionError(f"/qa/coverage-index chat partial row mismatch: {coverage_index}")
    if runtime_group.get("chatQualityBroadQualityComplete") != matrix.get("broadQualityComplete"):
        raise AssertionError(f"/qa/coverage-index chat quality boundary mismatch: {coverage_index}")
    if runtime_group.get("chatQualityProofFileParity") != matrix.get("proofFileParity"):
        raise AssertionError(f"/qa/coverage-index chat proof parity mismatch: {coverage_index}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        matrix = request("GET", ROUTE)
        state = request("GET", "/state")
        coverage_index = request("GET", "/qa/coverage-index", timeout=120.0)
        assert_matrix(matrix, state, coverage_index)
        print("chat-quality-evidence-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"chat-quality-evidence-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
