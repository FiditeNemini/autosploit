#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
RELEASE_APP_BINARY = ROOT / "release" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"


def request(method: str, path: str, body: str | dict | None = None, timeout: float = 8.0):
    if isinstance(body, dict):
        body = json.dumps(body)
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


def launch(env: dict[str, str]) -> subprocess.Popen:
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.environ.get("EXPLOITBOT_PERSISTENCE_PROOF_RELEASE_APP") == "1":
        if not RELEASE_APP_BINARY.is_file():
            raise RuntimeError("release app binary missing; run release-readiness proof first")
        app = subprocess.Popen([str(RELEASE_APP_BINARY)], cwd=ROOT, env=env)
    else:
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
    wait_for_app()
    return app


def stop(app: subprocess.Popen | None) -> None:
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if app is not None and app.poll() is None:
        app.send_signal(signal.SIGTERM)


def assert_persisted_state() -> None:
    state = request("GET", "/state")
    messages = request("GET", "/messages")
    results = request("GET", "/results")

    context = state.get("contextCatalog") or {}
    if context.get("maxSnippets") != 5 or context.get("includeAssets") is not False:
        raise AssertionError(f"context settings did not persist: {state}")
    if state.get("chat", {}).get("maxIterations") != 9:
        raise AssertionError(f"chat settings did not persist: {state}")
    if state.get("chat", {}).get("enableReasoning") is not False:
        raise AssertionError(f"reasoning toggle did not persist: {state}")
    engine = state.get("engineConfig") or {}
    expected_engine = {
        "modelPath": "/Users/eric/models/JANGQ/Qwen3.6-27B-JANG_4M-MTP",
        "reasoningParser": "qwen3",
        "toolCallParser": "qwen",
        "kvCacheQuantization": "none",
        "useModelGenerationDefaults": False,
        "temperature": 0.42,
        "topP": 0.77,
        "maxTokens": 321,
        "prefixCache": False,
        "promptL2Disk": False,
        "diskCacheMaxGB": 3.5,
        "cacheMemoryPercent": 0.55,
        "pagedCache": False,
        "pagedCacheBlockSize": 128,
        "blockL2Disk": False,
        "blockDiskCacheMaxGB": 4.5,
        "kvCacheGroupSize": 32,
    }
    for key, expected in expected_engine.items():
        if engine.get(key) != expected:
            raise AssertionError(f"engine setting {key} did not persist: expected {expected!r}, got {engine.get(key)!r}; state={state}")
    if not any("QA-PERSIST-USER" in msg.get("content", "") for msg in messages):
        raise AssertionError(f"persisted user message missing: {messages}")
    if not any(msg.get("tool") == "nmap" and "QA-PERSIST-TOOL" in msg.get("content", "") for msg in messages):
        raise AssertionError(f"persisted tool message missing: {messages}")
    if not any(port.get("port") == 443 and port.get("service") == "https" for port in results.get("ports", [])):
        raise AssertionError(f"result store did not rebuild nmap port from persisted tool message: {results}")
    if state.get("ports") != 1:
        raise AssertionError(f"state did not expose rebuilt port count: {state}")


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="exploitbot-persist-home-") as home:
        data_dir = Path(home) / ".exploitbot" / "data"
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = home
        env["EXPLOITBOT_DATA_DIR"] = str(data_dir)
        app: subprocess.Popen | None = None
        try:
            app = launch(env)
            seeded = request("POST", "/qa/seed-persistence-fixture")
            if seeded.get("ok") is not True:
                raise AssertionError(f"persistence fixture seed failed: {seeded}")
            configured = request("POST", "/qa/apply-app-settings", {
                "maxIterations": 9,
                "chat": {"enableReasoning": False},
                "engine": {
                    "modelPath": "/Users/eric/models/JANGQ/Qwen3.6-27B-JANG_4M-MTP",
                    "reasoningParser": "qwen3",
                    "toolCallParser": "qwen",
                    "kvCacheQuantization": "none",
                    "useModelGenerationDefaults": False,
                    "temperature": 0.42,
                    "topP": 0.77,
                    "maxTokens": 321,
                    "prefixCache": False,
                    "diskCache": False,
                    "diskCacheMaxGB": 3.5,
                    "cacheMemoryPercent": 0.55,
                    "pagedCache": False,
                    "pagedCacheBlockSize": 128,
                    "blockDiskCache": False,
                    "blockDiskCacheMaxGB": 4.5,
                    "kvCacheGroupSize": 32,
                },
            })
            if configured.get("ok") is not True:
                raise AssertionError(f"persistence settings configuration failed: {configured}")
            assert_persisted_state()

            stop(app)
            app = launch(env)
            assert_persisted_state()

            print("persistence proof passed")
        finally:
            stop(app)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"persistence proof failed: {exc}", flush=True)
        raise SystemExit(1)
