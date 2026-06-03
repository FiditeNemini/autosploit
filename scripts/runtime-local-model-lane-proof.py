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
    "smallestLocalQwenSelection",
    "releaseAppQwenLiveChat",
    "qwenRepeatCacheReuse",
    "qwenHybridSSMTopology",
    "qwenTurboQuantKV",
    "qwenContinuousBatchingLowRAM",
    "minimaxSmallReleaseLane",
    "activeFamiliesExcludeZaya",
]

EXPECTED_CONTRACTS = {
    "qwenTargetExists",
    "qwenReleaseLiveArtifact",
    "qwenReleaseLiveModelMatches",
    "qwenReleaseChatNonEmpty",
    "qwenRepeatCacheReuse",
    "qwenLowRAMCeiling",
    "qwenHybridSSMTopology",
    "qwenTurboQuantKV",
    "qwenPrefixPagedBlockCache",
    "qwenContinuousBatchingArtifact",
    "qwenContinuousBatchingLowRAM",
    "minimaxTargetExists",
    "minimaxReleaseArtifact",
    "minimaxTurboQuantKV",
    "activeFamiliesOnlyQwenMiniMax",
    "noZayaActiveArtifacts",
    "coverageIndexMirror",
    "deepRuntimeMirror",
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

        payload = request("GET", "/qa/runtime-local-model-lane")
        if payload.get("ok") is not True:
            raise AssertionError(f"runtime local model lane route failed: {payload}")
        if payload.get("route") != "/qa/runtime-local-model-lane":
            raise AssertionError(f"runtime local model lane route label mismatch: {payload}")
        if payload.get("proofLevel") != "local-model-folder-and-live-artifact-backed":
            raise AssertionError(f"runtime local model lane proof level mismatch: {payload}")
        if payload.get("rows") != EXPECTED_ROWS:
            raise AssertionError(f"runtime local model lane row order mismatch: {payload}")
        if payload.get("rowCount") != len(EXPECTED_ROWS):
            raise AssertionError(f"runtime local model lane row count mismatch: {payload}")
        if payload.get("qwenTargetPath") != "/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP":
            raise AssertionError(f"runtime local Qwen target mismatch: {payload}")
        if payload.get("qwenReleaseAppArtifact") != "docs/live-proofs/2026-06-03-release-app-qwen-mxfp4-live.json":
            raise AssertionError(f"runtime local Qwen release artifact mismatch: {payload}")
        if payload.get("qwenReleasePreview") != "RELEASE-QWEN-OK":
            raise AssertionError(f"runtime local Qwen chat preview mismatch: {payload}")
        if payload.get("qwenSecondCachedTokens", 0) < 1:
            raise AssertionError(f"runtime local Qwen cached tokens missing: {payload}")
        if payload.get("qwenActiveMemoryMB", 0) <= 0 or payload.get("qwenActiveMemoryMB", 0) > 20000:
            raise AssertionError(f"runtime local Qwen low-RAM ceiling mismatch: {payload}")
        if payload.get("qwenTopologyName") != "hybrid_ssm_attention":
            raise AssertionError(f"runtime local Qwen topology mismatch: {payload}")
        if payload.get("qwenKVCacheBits") != 4:
            raise AssertionError(f"runtime local Qwen KV bits mismatch: {payload}")
        if payload.get("qwenContinuousBatchingArtifactOK") is not True:
            raise AssertionError(f"runtime local Qwen continuous batching artifact mismatch: {payload}")
        if payload.get("qwenContinuousBatchingActiveMemoryMB", 0) <= 0 or payload.get("qwenContinuousBatchingActiveMemoryMB", 0) > 20000:
            raise AssertionError(f"runtime local Qwen continuous batching low-RAM ceiling mismatch: {payload}")
        if payload.get("minimaxTargetPath") != "/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ":
            raise AssertionError(f"runtime local MiniMax target mismatch: {payload}")
        if payload.get("minimaxKVCacheBits") != 4:
            raise AssertionError(f"runtime local MiniMax KV bits mismatch: {payload}")
        if payload.get("activeFamilies") != ["qwen", "minimax"]:
            raise AssertionError(f"runtime local active families mismatch: {payload}")
        if payload.get("excludedFamilies") != ["zaya"]:
            raise AssertionError(f"runtime local excluded families mismatch: {payload}")

        contracts = payload.get("contracts") or {}
        missing_contracts = sorted(name for name in EXPECTED_CONTRACTS if contracts.get(name) is not True)
        if missing_contracts:
            raise AssertionError(f"runtime local model lane missing contracts {missing_contracts}: {payload}")
        if payload.get("contractCount") != len(EXPECTED_CONTRACTS):
            raise AssertionError(f"runtime local model lane contract count mismatch: {payload}")
        if payload.get("contractParity") is not True:
            raise AssertionError(f"runtime local model lane contract parity mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"runtime local model lane proof-file parity mismatch: {payload}")
        if payload.get("artifactFileParity") is not True:
            raise AssertionError(f"runtime local model lane artifact-file parity mismatch: {payload}")

        state = request("GET", "/state")
        routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/runtime-local-model-lane" not in routes:
            raise AssertionError(f"state route list missing runtime local model lane: {routes}")

        deep = request("GET", "/qa/deep-runtime-flow-coverage")
        if "/qa/runtime-local-model-lane" not in (deep.get("routes") or []):
            raise AssertionError(f"deep runtime flow missing local model lane route: {deep}")
        if deep.get("runtimeLocalModelLaneContractParity") is not True:
            raise AssertionError(f"deep runtime flow missing local model lane parity: {deep}")

        index = request("GET", "/qa/coverage-index")
        runtime_group = (index.get("groups") or {}).get("runtimeAndCache") or {}
        if "/qa/runtime-local-model-lane" not in (runtime_group.get("endpoints") or []):
            raise AssertionError(f"coverage index runtime group missing local model lane route: {runtime_group}")
        if runtime_group.get("runtimeLocalModelLaneContractParity") is not True:
            raise AssertionError(f"coverage index missing local model lane parity: {runtime_group}")

        print("runtime-local-model-lane proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"runtime-local-model-lane proof failed: {exc}", flush=True)
        raise SystemExit(1)
