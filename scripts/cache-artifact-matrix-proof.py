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
    "qwenReleaseCrossRestartCacheHit",
    "qwenBlockL2Storage",
    "qwenTurboQuantKV",
    "qwenHybridSSMAsyncReDerive",
    "qwenContinuousBatchingCache",
    "minimaxTurboQuantKV",
    "minimaxBlockL2Storage",
]

EXPECTED_ARTIFACTS = {
    "docs/live-proofs/checkpoint-463-release-app-qwen-cross-restart-cache.json",
    "docs/live-proofs/checkpoint-112-qwen-hybrid-block-l2-ssm-restart-replay-live.json",
    "docs/live-proofs/checkpoint-452-qwen-continuous-batching-live.json",
    "docs/live-proofs/checkpoint-110-minimax-restart-replay-live.json",
    "docs/live-proofs/checkpoint-111-minimax-block-l2-restart-replay-live.json",
    "docs/live-proofs/checkpoint-102-block-l2-partial-proof.json",
}

EXPECTED_CONTRACTS = {
    "qwenReleaseCrossRestartOK",
    "qwenSchedulerDiskHit",
    "qwenSchedulerTokensSaved",
    "qwenBlockL2DiskHit",
    "qwenSSMCompanionDiskHit",
    "qwenBlockL2Store",
    "qwenBlockL2ReadHit",
    "qwenTurboQuantQ4",
    "qwenSSMAsyncReDerive",
    "qwenBatchingTurboQuantQ4",
    "qwenBatchingBlockL2Writes",
    "qwenBatchingSSMReDerive",
    "minimaxTurboQuantQ4",
    "minimaxBlockL2Writes",
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

        payload = request("GET", "/qa/cache-artifact-matrix")
        if payload.get("ok") is not True:
            raise AssertionError(f"cache artifact matrix route failed: {payload}")
        if payload.get("route") != "/qa/cache-artifact-matrix":
            raise AssertionError(f"cache artifact matrix route label mismatch: {payload}")
        if payload.get("proofLevel") != "live-artifact-backed":
            raise AssertionError(f"cache artifact matrix proof level mismatch: {payload}")
        if payload.get("rows") != EXPECTED_ROWS:
            raise AssertionError(f"cache artifact matrix row order mismatch: {payload}")
        if set(payload.get("artifacts") or []) != EXPECTED_ARTIFACTS:
            raise AssertionError(f"cache artifact matrix artifact set mismatch: {payload}")
        if payload.get("artifactFileParity") is not True:
            raise AssertionError(f"cache artifact matrix artifact parity mismatch: {payload}")

        metrics = payload.get("metrics") or {}
        minimums = {
            "qwenReleaseSchedulerDiskHits": 1,
            "qwenReleaseSchedulerTokensSaved": 1,
            "qwenReleaseBlockL2DiskHits": 1,
            "qwenReleaseSSMDiskHits": 1,
            "blockL2ProofDiskWrites": 2,
            "blockL2ProofDiskHits": 2,
            "qwenHybridSSMReDeriveLastTokens": 1,
            "qwenBatchingBlockL2DiskWrites": 1,
            "qwenBatchingSSMReDeriveCompleted": 1,
            "minimaxBlockL2DiskWrites": 1,
        }
        for key, minimum in minimums.items():
            if int(metrics.get(key) or 0) < minimum:
                raise AssertionError(f"cache artifact metric {key} below {minimum}: {payload}")
        if metrics.get("qwenHybridKVBits") != 4:
            raise AssertionError(f"qwen hybrid KV bits mismatch: {payload}")
        if metrics.get("qwenBatchingKVBits") != 4:
            raise AssertionError(f"qwen batching KV bits mismatch: {payload}")
        if metrics.get("minimaxKVBits") != 4:
            raise AssertionError(f"minimax KV bits mismatch: {payload}")

        contracts = payload.get("contracts") or {}
        missing = sorted(name for name in EXPECTED_CONTRACTS if contracts.get(name) is not True)
        if missing:
            raise AssertionError(f"cache artifact matrix missing contracts {missing}: {payload}")
        if payload.get("contractCount") != len(EXPECTED_CONTRACTS):
            raise AssertionError(f"cache artifact matrix contract count mismatch: {payload}")
        if payload.get("contractParity") is not True:
            raise AssertionError(f"cache artifact matrix contract parity mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"cache artifact matrix proof-file parity mismatch: {payload}")

        state = request("GET", "/state")
        routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/cache-artifact-matrix" not in routes:
            raise AssertionError(f"state route list missing cache artifact matrix route: {routes}")

        runtime = request("GET", "/qa/runtime-coverage")
        if runtime.get("cacheArtifactMatrixContractParity") is not True:
            raise AssertionError(f"runtime coverage missing cache artifact matrix parity: {runtime}")

        index = request("GET", "/qa/coverage-index")
        runtime_group = (index.get("groups") or {}).get("runtimeAndCache") or {}
        if "/qa/cache-artifact-matrix" not in (runtime_group.get("endpoints") or []):
            raise AssertionError(f"coverage index runtime group missing cache artifact matrix route: {runtime_group}")
        if runtime_group.get("cacheArtifactMatrixContractParity") is not True:
            raise AssertionError(f"coverage index missing cache artifact matrix parity: {runtime_group}")

        print("cache-artifact-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"cache-artifact-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
