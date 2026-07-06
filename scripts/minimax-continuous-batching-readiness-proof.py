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
EXPECTED_MODEL = "/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ"
EXPECTED_ARTIFACT = "docs/live-proofs/checkpoint-464-minimax-continuous-batching-live.json"
EXPECTED_SCRIPT = "prove-live-minimax-continuous-batching.py"


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

        coverage = request("GET", "/qa/continuous-batching-coverage")
        index = request("GET", "/qa/coverage-index", timeout=120.0)
        runtime_group = (index.get("groups") or {}).get("runtimeAndCache") or {}

        if coverage.get("minimaxContinuousBatchingModel") != EXPECTED_MODEL:
            raise AssertionError(f"MiniMax batching model path mismatch: {coverage}")
        if coverage.get("minimaxContinuousBatchingArtifact") != EXPECTED_ARTIFACT:
            raise AssertionError(f"MiniMax batching artifact path mismatch: {coverage}")
        if coverage.get("minimaxContinuousBatchingArtifactRequired") is not True:
            raise AssertionError(f"MiniMax batching artifact should be required: {coverage}")
        if coverage.get("minimaxContinuousBatchingLiveReady") is not True:
            raise AssertionError(f"MiniMax batching live-ready flag missing: {coverage}")
        if coverage.get("minimaxContinuousBatchingArtifactOK") is not True:
            raise AssertionError(f"MiniMax batching artifact OK flag missing: {coverage}")
        if coverage.get("minimaxContinuousBatchingMaxRunningObserved", 0) < 2:
            raise AssertionError(f"MiniMax batching max running too low: {coverage}")
        if coverage.get("minimaxContinuousBatchingMaxWaitingObserved", 0) < 2:
            raise AssertionError(f"MiniMax batching max waiting too low: {coverage}")
        if coverage.get("minimaxContinuousBatchingRequestsProcessed", 0) < 2:
            raise AssertionError(f"MiniMax batching processed too few requests: {coverage}")
        if coverage.get("minimaxContinuousBatchingKVBits") != 4:
            raise AssertionError(f"MiniMax batching KV bits mismatch: {coverage}")
        if coverage.get("minimaxContinuousBatchingBlockL2DiskWrites", 0) < 1:
            raise AssertionError(f"MiniMax batching block L2 writes missing: {coverage}")
        if not coverage.get("minimaxContinuousBatchingNextCommand"):
            raise AssertionError(f"MiniMax batching next command missing: {coverage}")
        if EXPECTED_SCRIPT not in coverage.get("minimaxContinuousBatchingNextCommand"):
            raise AssertionError(f"MiniMax batching next command does not name proof script: {coverage}")
        if EXPECTED_SCRIPT not in (coverage.get("proofs") or []):
            raise AssertionError(f"MiniMax live batching proof script missing from route proof list: {coverage}")
        if EXPECTED_SCRIPT not in (runtime_group.get("proofs") or []):
            raise AssertionError(f"MiniMax live batching proof script missing from coverage index: {runtime_group}")

        mirrored = {
            "minimaxContinuousBatchingArtifact",
            "minimaxContinuousBatchingArtifactExists",
            "minimaxContinuousBatchingArtifactOK",
            "minimaxContinuousBatchingLiveReady",
            "minimaxContinuousBatchingNextCommand",
        }
        for key in mirrored:
            if runtime_group.get(key) != coverage.get(key):
                raise AssertionError(f"coverage index MiniMax batching mirror mismatch for {key}: {runtime_group}")

        print("minimax-continuous-batching-readiness proof passed")
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
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"minimax-continuous-batching-readiness proof failed: {exc}", flush=True)
        raise SystemExit(1)
