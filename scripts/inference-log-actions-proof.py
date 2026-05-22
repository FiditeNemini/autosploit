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

        seeded = request("POST", "/qa/seed-inference-log-actions")
        if seeded.get("ok") is not True:
            raise AssertionError(f"inference log seed failed: {seeded}")
        state = request("GET", "/state")
        logs = state.get("inferenceLogActions") or {}
        if logs.get("engineLogChars", 0) <= 0:
            raise AssertionError(f"seed did not expose engine log chars: {logs}")

        response = request("POST", "/qa/inference-log-action", {"action": "copy"})
        if response.get("ok") is not True:
            raise AssertionError(f"inference log copy action failed: {response}")
        state = request("GET", "/state")
        logs = state.get("inferenceLogActions") or {}
        if logs.get("lastAction") != "copy" or logs.get("status") != "done":
            raise AssertionError(f"inference log copy action state missing: {logs}")
        if "QA engine log line 1" not in logs.get("clipboardPreview", ""):
            raise AssertionError(f"inference log copy preview missing: {logs}")

        response = request("POST", "/qa/inference-log-action", {"action": "clear"})
        if response.get("ok") is not True:
            raise AssertionError(f"inference log clear action failed: {response}")
        state = request("GET", "/state")
        logs = state.get("inferenceLogActions") or {}
        if logs.get("lastAction") != "clear" or logs.get("status") != "done":
            raise AssertionError(f"inference log action state missing: {logs}")
        if logs.get("engineLogChars") != 0:
            raise AssertionError(f"inference log was not cleared: {logs}")
        feed = state.get("feedRecent") or []
        if not any("clearInferenceLog" in entry.get("text", "") for entry in feed):
            raise AssertionError(f"inference log clear not visible in activity feed: {feed}")

        print("inference-log-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"inference-log-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
