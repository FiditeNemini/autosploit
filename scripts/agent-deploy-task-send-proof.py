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


def run() -> None:
    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-agent-task-send-home-")
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

        request("POST", "/engine/mock", "http://127.0.0.1:18993")
        seeded = request("POST", "/qa/seed-agent-actions")
        if seeded.get("ok") is not True:
            raise AssertionError(f"agent seed failed: {seeded}")

        deployed = request("POST", "/qa/agent-action", {
            "action": "deployAgent",
            "name": "QA Task Send Agent",
            "task": "Inspect the seeded context and report back.",
            "type": "Custom",
        })
        if deployed.get("ok") is not True:
            raise AssertionError(f"agent deploy failed: {deployed}")

        state = request("GET", "/state")
        actions = state.get("agentActions") or {}
        if actions.get("lastAction") != "deployAgent" or actions.get("status") != "done":
            raise AssertionError(f"agent deploy action state missing: {actions}")
        if actions.get("taskSent") is not True:
            raise AssertionError(f"agent deploy did not expose taskSent: {actions}")
        if actions.get("messageCount", 0) < 1:
            raise AssertionError(f"agent deploy did not expose message count: {actions}")
        agent = next((item for item in state.get("agents", {}).get("details") or [] if item.get("name") == "QA Task Send Agent"), None)
        if not agent:
            raise AssertionError(f"new agent not present: {state}")
        if agent.get("messageCount", 0) < 1:
            raise AssertionError(f"agent task was not appended to agent chat: {agent}")

        print("agent-deploy-task-send proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
        temp_home.cleanup()


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"agent-deploy-task-send proof failed: {exc}", flush=True)
        raise SystemExit(1)
