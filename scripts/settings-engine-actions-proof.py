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
MOCK_ENGINE = "http://127.0.0.1:18991"


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


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        mocked = request("POST", "/engine/mock", MOCK_ENGINE)
        if mocked.get("ok") is not True:
            raise AssertionError(f"mock engine setup failed: {mocked}")
        before = request("GET", "/state")
        if before.get("engineRunning") is not True:
            raise AssertionError(f"mock engine did not mark running: {before}")

        stopped = request("POST", "/engine/stop")
        if stopped.get("ok") is not True:
            raise AssertionError(f"engine stop failed: {stopped}")
        after = request("GET", "/state")
        if after.get("engineRunning") is not False:
            raise AssertionError(f"engine did not stop: {after}")
        actions = after.get("settingsEngineActions") or {}
        if actions.get("status") != "done" or actions.get("lastAction") != "stopEngine":
            raise AssertionError(f"missing settings engine stop action state: {actions}")
        if actions.get("wasRunning") is not True or actions.get("isRunning") is not False:
            raise AssertionError(f"wrong settings engine stop running flags: {actions}")
        if actions.get("model") != "mock-qwen-jang":
            raise AssertionError(f"settings engine action did not preserve model label: {actions}")
        feed = after.get("feedRecent") or []
        if not any("stopEngine" in entry.get("text", "") for entry in feed):
            raise AssertionError(f"settings engine stop not visible in activity feed: {feed}")

        print("settings-engine-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"settings-engine-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
