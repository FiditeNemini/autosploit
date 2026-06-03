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


EXPECTED_DEFAULTS = {
    "reasoningParser": "auto",
    "toolCallParser": "auto",
    "kvCacheQuantization": "turboquant-q4",
    "useModelGenerationDefaults": True,
    "prefixCache": True,
    "promptL2Disk": True,
    "pagedCache": True,
    "blockL2Disk": True,
    "cacheMemoryPercent": 0.30,
    "diskCacheMaxGB": 10.0,
    "blockDiskCacheMaxGB": 10.0,
    "pagedCacheBlockSize": 64,
    "maxTokens": 4096,
}

EXPECTED_ENGINE_ARGS = {
    "--reasoning-parser",
    "--tool-call-parser",
    "--kv-cache-quantization",
    "--enable-prefix-cache",
    "--enable-disk-cache",
    "--use-paged-cache",
    "--enable-block-disk-cache",
    "--cache-memory-percent",
    "--max-num-seqs",
}

EXPECTED_CONTRACTS = {
    "stateDefaults",
    "settingsApplyForcesRequiredCache",
    "engineLaunchArgs",
    "parserAutoDefaults",
    "turboQuantDefault",
    "l2DiskDefaults",
    "pagedCacheDefault",
    "modelGenerationDefaults",
    "continuousBatchingStartup",
    "persistentEngineConfig",
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

        payload = request("GET", "/qa/startup-cache-defaults")
        if payload.get("ok") is not True:
            raise AssertionError(f"startup cache defaults route failed: {payload}")
        if payload.get("route") != "/qa/startup-cache-defaults":
            raise AssertionError(f"startup cache defaults route label mismatch: {payload}")
        if payload.get("proofLevel") != "app-state-source-and-settings-backed":
            raise AssertionError(f"startup cache defaults proof level mismatch: {payload}")
        defaults = payload.get("defaults") or {}
        for key, expected in EXPECTED_DEFAULTS.items():
            if defaults.get(key) != expected:
                raise AssertionError(f"startup default {key} mismatch: {payload}")
        engine_args = set(payload.get("engineLaunchArgs") or [])
        missing_args = sorted(EXPECTED_ENGINE_ARGS.difference(engine_args))
        if missing_args:
            raise AssertionError(f"startup defaults missing engine launch args {missing_args}: {payload}")
        if payload.get("cacheResponseMethod") != "prefix-cache-l2-turboquant":
            raise AssertionError(f"startup cache response method mismatch: {payload}")
        if payload.get("newModelSessionBehavior") != "new-context-window-preserve-engine-cache-session":
            raise AssertionError(f"startup new-model session behavior mismatch: {payload}")

        contracts = payload.get("contracts") or {}
        missing_contracts = sorted(name for name in EXPECTED_CONTRACTS if contracts.get(name) is not True)
        if missing_contracts:
            raise AssertionError(f"startup cache defaults missing contracts {missing_contracts}: {payload}")
        if payload.get("contractCount") != len(EXPECTED_CONTRACTS):
            raise AssertionError(f"startup cache defaults contract count mismatch: {payload}")
        if payload.get("contractParity") is not True:
            raise AssertionError(f"startup cache defaults contract parity mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"startup cache defaults proof-file parity mismatch: {payload}")

        state = request("GET", "/state")
        if "/qa/startup-cache-defaults" not in ((state.get("qaCoverage") or {}).get("stateRoutes") or []):
            raise AssertionError(f"state route list missing startup cache defaults route: {state.get('qaCoverage')}")
        settings = request("GET", "/qa/settings-coverage")
        if settings.get("startupCacheDefaultsContractParity") is not True:
            raise AssertionError(f"settings coverage missing startup defaults parity: {settings}")
        runtime = request("GET", "/qa/runtime-coverage")
        if runtime.get("startupCacheDefaultsContractParity") is not True:
            raise AssertionError(f"runtime coverage missing startup defaults parity: {runtime}")

        print("startup-cache-defaults proof passed")
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
        print(f"startup-cache-defaults proof failed: {exc}", flush=True)
        raise SystemExit(1)
