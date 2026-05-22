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


def request(method: str, path: str, body: str | None = None, timeout: float = 8.0):
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


def assert_action(action: str, expected_count: int, expected_preview: str) -> None:
    response = request("POST", "/qa/activity-action", action)
    if response.get("ok") is not True:
        raise AssertionError(f"activity action failed for {action}: {response}")

    state = request("GET", "/state")
    activity = state.get("activityFeedActions") or {}
    if activity.get("lastAction") != action or activity.get("status") != "done":
        raise AssertionError(f"activity action state missing for {action}: {activity}")
    if activity.get("count") != expected_count:
        raise AssertionError(f"activity action count wrong for {action}: {activity}")
    if expected_preview and expected_preview not in activity.get("clipboardPreview", ""):
        raise AssertionError(f"activity action preview wrong for {action}: {activity}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-activity-actions")
        if seeded.get("ok") is not True:
            raise AssertionError(f"activity action seed failed: {seeded}")

        assert_action("copyEntry", 1, "Running nmap")
        assert_action("copyEntryTimestamp", 1, "Running nmap")
        assert_action("copyVisible", 3, "Finding created")
        assert_action("clear", 0, "")

        state = request("GET", "/state")
        if state.get("feedEntries") != 0:
            raise AssertionError(f"activity clear did not empty feed: {state}")

        print("activity-feed-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"activity-feed-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
