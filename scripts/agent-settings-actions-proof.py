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


def assert_settings_action(action: str, *, enabled: bool, max_agents: int, active_agents: int) -> None:
    state = request("GET", "/state")
    agents = state.get("agents") or {}
    if agents.get("multiAgentEnabled") is not enabled:
        raise AssertionError(f"multi-agent enabled mismatch after {action}: {agents}")
    if agents.get("maxConcurrentAgents") != max_agents:
        raise AssertionError(f"max concurrent mismatch after {action}: {agents}")
    if agents.get("activeAgents") != active_agents:
        raise AssertionError(f"active agent count mismatch after {action}: {agents}")
    actions = state.get("agentActions") or {}
    if actions.get("lastAction") != action or actions.get("status") != "done":
        raise AssertionError(f"agent settings action missing after {action}: {actions}")
    if actions.get("agentCount") != active_agents:
        raise AssertionError(f"agent action count mismatch after {action}: {actions}")
    feed = state.get("feedRecent") or []
    if not any(action in entry.get("text", "") for entry in feed):
        raise AssertionError(f"agent settings action {action} not visible in activity feed: {feed}")


def run() -> None:
    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-agent-settings-home-")
    try:
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = temp_home.name
        env["EXPLOITBOT_DATA_DIR"] = str(Path(temp_home.name) / ".exploitbot" / "data")
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-agent-actions")
        if seeded.get("ok") is not True:
            raise AssertionError(f"agent action seed failed: {seeded}")

        response = request("POST", "/qa/agent-settings-action", {"action": "setMaxConcurrentAgents", "value": 2})
        if response.get("ok") is not True:
            raise AssertionError(f"agent max setting failed: {response}")
        assert_settings_action("setMaxConcurrentAgents", enabled=True, max_agents=2, active_agents=2)

        response = request("POST", "/qa/agent-settings-action", {"action": "setMultiAgentEnabled", "enabled": False})
        if response.get("ok") is not True:
            raise AssertionError(f"agent disable setting failed: {response}")
        assert_settings_action("setMultiAgentEnabled", enabled=False, max_agents=2, active_agents=0)

        response = request("POST", "/qa/agent-settings-action", {"action": "setMultiAgentEnabled", "enabled": True})
        if response.get("ok") is not True:
            raise AssertionError(f"agent enable setting failed: {response}")
        assert_settings_action("setMultiAgentEnabled", enabled=True, max_agents=2, active_agents=0)

        print("agent-settings-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
        temp_home.cleanup()


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"agent-settings-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
