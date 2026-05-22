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


def request(method: str, path: str, body: dict | None = None, timeout: float = 8.0):
    data = None if body is None else json.dumps(body).encode("utf-8")
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


def agent_action(state: dict) -> dict:
    action = state.get("agentActions") or {}
    if not isinstance(action, dict):
        raise AssertionError(f"missing agent action state: {state}")
    return action


def agent_count(state: dict) -> int:
    return len((state.get("agents") or {}).get("details") or [])


def run() -> None:
    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-agent-sheet-home-")
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
            raise AssertionError(f"agent seed failed: {seeded}")
        state = request("GET", "/state")
        before_count = agent_count(state)

        opened = request("POST", "/qa/agent-deploy-sheet", {"action": "open"})
        if opened.get("ok") is not True:
            raise AssertionError(f"agent deploy sheet open failed: {opened}")
        state = request("GET", "/state")
        action = agent_action(state)
        if action.get("lastAction") != "openDeploySheet" or action.get("deploySheetVisible") is not True:
            raise AssertionError(f"agent deploy sheet open state wrong: {action}")

        cancelled = request("POST", "/qa/agent-deploy-sheet", {"action": "cancel"})
        if cancelled.get("ok") is not True:
            raise AssertionError(f"agent deploy sheet cancel failed: {cancelled}")
        state = request("GET", "/state")
        action = agent_action(state)
        if action.get("lastAction") != "cancelDeploySheet" or action.get("deploySheetVisible") is not False:
            raise AssertionError(f"agent deploy sheet cancel state wrong: {action}")
        if agent_count(state) != before_count:
            raise AssertionError(f"cancel changed agent count: {state}")

        request("POST", "/qa/agent-deploy-sheet", {"action": "open"})
        deployed = request("POST", "/qa/agent-deploy-sheet", {
            "action": "deploy",
            "name": "QA Sheet Agent",
            "task": "Validate the visible deploy-sheet wiring.",
            "type": "Recon",
        })
        if deployed.get("ok") is not True:
            raise AssertionError(f"agent deploy sheet deploy failed: {deployed}")
        state = request("GET", "/state")
        action = agent_action(state)
        if action.get("lastAction") != "deployAgent" or action.get("deploySheetVisible") is not False:
            raise AssertionError(f"agent deploy sheet final state wrong: {action}")
        if action.get("agentName") != "QA Sheet Agent" or action.get("agentType") != "Recon Agent":
            raise AssertionError(f"agent deploy sheet target wrong: {action}")
        if agent_count(state) != before_count + 1:
            raise AssertionError(f"deploy did not add agent: {state}")

        feed = state.get("feedRecent") or []
        if not any("deployAgent QA Sheet Agent" in entry.get("text", "") for entry in feed):
            raise AssertionError(f"sheet deploy not visible in activity feed: {feed}")

        print("agent-deploy-sheet proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
        temp_home.cleanup()


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"agent-deploy-sheet proof failed: {exc}", flush=True)
        raise SystemExit(1)
