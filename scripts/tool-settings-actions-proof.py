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


def assert_action(action: str, *, tool_name: str, installed: int, missing: int, log_marker: str) -> None:
    state = request("GET", "/state")
    settings = state.get("toolSettings") or {}
    actions = state.get("toolSettingsActions") or {}
    if actions.get("lastAction") != action or actions.get("status") != "done":
        raise AssertionError(f"tool action state missing for {action}: {actions}")
    if actions.get("toolName") != tool_name:
        raise AssertionError(f"tool action name wrong for {action}: {actions}")
    if actions.get("installedCount") != installed or actions.get("missingCount") != missing:
        raise AssertionError(f"tool action counts wrong for {action}: {actions}")
    if settings.get("installedCount") != installed or settings.get("missingCount") != missing:
        raise AssertionError(f"tool settings counts wrong for {action}: {settings}")
    if log_marker not in settings.get("installLog", ""):
        raise AssertionError(f"tool install log missing marker {log_marker!r}: {settings}")
    feed = state.get("feedRecent") or []
    if not any(action in entry.get("text", "") for entry in feed):
        raise AssertionError(f"tool action {action} was not reflected in activity feed: {feed}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-tool-settings-status")
        if seeded.get("ok") is not True:
            raise AssertionError(f"tool settings seed failed: {seeded}")

        response = request("POST", "/qa/tool-settings-action", {"action": "refresh"})
        if response.get("ok") is not True:
            raise AssertionError(f"tool refresh action failed: {response}")
        assert_action("refresh", tool_name="all", installed=2, missing=1, log_marker="refresh")

        response = request("POST", "/qa/tool-settings-action", {"action": "install", "toolName": "sqlmap"})
        if response.get("ok") is not True:
            raise AssertionError(f"tool install action failed: {response}")
        assert_action("install", tool_name="sqlmap", installed=3, missing=0, log_marker="installed sqlmap")

        response = request("POST", "/qa/seed-tool-settings-status")
        if response.get("ok") is not True:
            raise AssertionError(f"tool settings reseed failed: {response}")
        response = request("POST", "/qa/tool-settings-action", {"action": "installAllMissing"})
        if response.get("ok") is not True:
            raise AssertionError(f"tool install all action failed: {response}")
        assert_action("installAllMissing", tool_name="all", installed=3, missing=0, log_marker="installed 1 missing")

        print("tool-settings-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"tool-settings-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
