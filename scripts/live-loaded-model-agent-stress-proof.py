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
ARTIFACT = "docs/live-proofs/checkpoint-466-qwen-live-agent-stress.json"


def request(method: str, path: str, body: str | dict | None = None, timeout: float = 45.0):
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except TimeoutError as exc:
        raise TimeoutError(f"timed out requesting {method} {path}") from exc
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

        payload = request("GET", "/qa/live-loaded-model-agent-stress")
        if payload.get("ok") is not True:
            raise AssertionError(f"live loaded-model agent stress route failed: {payload}")
        if payload.get("artifact") != ARTIFACT:
            raise AssertionError(f"live loaded-model agent artifact mismatch: {payload}")
        if payload.get("artifactOK") is not True:
            raise AssertionError(f"live loaded-model agent artifact not accepted: {payload}")
        if payload.get("family") != "qwen":
            raise AssertionError(f"live loaded-model agent family mismatch: {payload}")
        if payload.get("model") != "/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP":
            raise AssertionError(f"live loaded-model agent model mismatch: {payload}")
        if payload.get("agentCount", 0) < 2:
            raise AssertionError(f"live loaded-model agent count too low: {payload}")
        if payload.get("appMaxWorkingObserved", 0) < 2:
            raise AssertionError(f"live loaded-model app parallelism too low: {payload}")
        if payload.get("engineMaxRunningObserved", 0) < 2:
            raise AssertionError(f"live loaded-model engine parallelism too low: {payload}")
        if payload.get("engineRequestsProcessed", 0) < 2:
            raise AssertionError(f"live loaded-model engine request count too low: {payload}")
        if payload.get("kvBits") != 4:
            raise AssertionError(f"live loaded-model KV bits mismatch: {payload}")
        if payload.get("blockL2DiskWrites", 0) < 1:
            raise AssertionError(f"live loaded-model block L2 writes missing: {payload}")
        if payload.get("ssmReDeriveCompleted", 0) < 1:
            raise AssertionError(f"live loaded-model SSM rederive completions missing: {payload}")
        if payload.get("ssmReDeriveFailed") != 0:
            raise AssertionError(f"live loaded-model SSM rederive failures: {payload}")
        if payload.get("activeMemoryMB", 0) <= 0 or payload.get("activeMemoryMB", 0) >= 20000:
            raise AssertionError(f"live loaded-model memory outside low-RAM lane: {payload}")

        runtime = request("GET", "/qa/runtime-coverage", timeout=45.0)
        live = (runtime.get("liveProofs") or {}).get("qwen") or {}
        if live.get("loadedModelAgentStress") is not True:
            raise AssertionError(f"runtime coverage missing live agent stress proof: {runtime}")
        if runtime.get("qwenLiveAgentStressArtifactOK") is not True:
            raise AssertionError(f"runtime coverage missing live agent stress artifact flag: {runtime}")
        if runtime.get("qwenLiveAgentStressEngineMaxRunningObserved", 0) < 2:
            raise AssertionError(f"runtime coverage live agent stress concurrency too low: {runtime}")

        deep = request("GET", "/qa/deep-runtime-flow-coverage", timeout=45.0)
        if (deep.get("contracts") or {}).get("liveLoadedModelAgentStress") is not True:
            raise AssertionError(f"deep runtime missing live loaded-model agent stress contract: {deep}")
        if "/qa/live-loaded-model-agent-stress" not in (deep.get("routes") or []):
            raise AssertionError(f"deep runtime missing live loaded-model agent stress route: {deep}")

        index = request("GET", "/qa/coverage-index", timeout=120.0)
        runtime_group = (index.get("groups") or {}).get("runtimeAndCache") or {}
        if "/qa/live-loaded-model-agent-stress" not in (runtime_group.get("endpoints") or []):
            raise AssertionError(f"coverage index missing live loaded-model agent route: {runtime_group}")
        if runtime_group.get("qwenLiveAgentStressArtifactOK") is not True:
            raise AssertionError(f"coverage index missing live loaded-model agent artifact: {runtime_group}")

        print("live-loaded-model-agent-stress proof passed")
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
        print(f"live-loaded-model-agent-stress proof failed: {exc}", flush=True)
        raise SystemExit(1)
