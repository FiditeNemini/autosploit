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


def agent_names(state: dict) -> list[str]:
    return [agent.get("name", "") for agent in (state.get("agents", {}).get("details") or [])]


def active_agent_name(state: dict) -> str:
    for agent in state.get("agents", {}).get("details") or []:
        if agent.get("isActive") is True:
            return agent.get("name", "")
    return ""


def assert_agent_action(action: str, expected_name: str, expected_count: int, expected_active: str) -> None:
    state = request("GET", "/state")
    actions = state.get("agentActions") or {}
    if actions.get("lastAction") != action or actions.get("status") != "done":
        raise AssertionError(f"agent action state missing for {action}: {actions}")
    if actions.get("agentName") != expected_name:
        raise AssertionError(f"agent action name wrong for {action}: {actions}")
    if actions.get("agentCount") != expected_count:
        raise AssertionError(f"agent count wrong for {action}: {actions}")
    if active_agent_name(state) != expected_active:
        raise AssertionError(f"active agent wrong after {action}: {state}")
    feed = state.get("feedRecent") or []
    if not any(action in entry.get("text", "") for entry in feed):
        raise AssertionError(f"agent action {action} was not reflected in activity feed: {feed}")


def run() -> None:
    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-agent-actions-home-")
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
        state = request("GET", "/state")
        if agent_names(state) != ["QA Recon Agent", "QA Web Agent"]:
            raise AssertionError(f"agent seed names wrong: {state}")
        if active_agent_name(state) != "QA Recon Agent":
            raise AssertionError(f"agent seed active wrong: {state}")

        response = request("POST", "/qa/agent-action", {
            "action": "deployAgent",
            "name": "QA Extra Agent",
            "task": "Hold for operator",
            "type": "Custom",
        })
        if response.get("ok") is not True:
            raise AssertionError(f"agent deploy action failed: {response}")
        assert_agent_action("deployAgent", "QA Extra Agent", 3, "QA Recon Agent")

        response = request("POST", "/qa/agent-action", {"action": "switchAgent", "target": "web"})
        if response.get("ok") is not True:
            raise AssertionError(f"agent switch action failed: {response}")
        assert_agent_action("switchAgent", "QA Web Agent", 3, "QA Web Agent")

        response = request("POST", "/qa/agent-action", {"action": "removeAgent", "target": "active"})
        if response.get("ok") is not True:
            raise AssertionError(f"agent remove action failed: {response}")
        assert_agent_action("removeAgent", "QA Web Agent", 2, "QA Recon Agent")

        response = request("POST", "/qa/agent-action", {"action": "clearAgents"})
        if response.get("ok") is not True:
            raise AssertionError(f"agent clear action failed: {response}")
        assert_agent_action("clearAgents", "all", 0, "")

        print("agent-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
        temp_home.cleanup()


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"agent-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
