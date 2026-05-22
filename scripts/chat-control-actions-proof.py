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


def assert_control(
    action: str,
    *,
    reasoning: bool,
    inspector: bool,
    generation: int,
    message_count: int | None = None,
) -> dict:
    state = request("GET", "/state")
    control = state.get("chatControlActions") or {}
    if control.get("lastAction") != action or control.get("status") != "done":
        raise AssertionError(f"chat control action missing for {action}: {control}")
    if control.get("enableReasoning") is not reasoning:
        raise AssertionError(f"reasoning state wrong after {action}: {control}")
    if control.get("contextInspectorVisible") is not inspector:
        raise AssertionError(f"context inspector state wrong after {action}: {control}")
    if control.get("contextGeneration") != generation:
        raise AssertionError(f"context generation wrong after {action}: {control}")

    chat = state.get("chat") or {}
    if chat.get("enableReasoning") is not reasoning:
        raise AssertionError(f"chat state reasoning mismatch after {action}: {chat}")
    qa = state.get("qaChatVisual") or {}
    if qa.get("contextInspectorVisible") is not inspector:
        raise AssertionError(f"visual inspector mismatch after {action}: {qa}")
    context = state.get("contextWindow") or {}
    if context.get("generation") != generation:
        raise AssertionError(f"context window generation mismatch after {action}: {context}")
    if action == "startNewContext" and context.get("cacheResponsesMethod") != "prefix-cache-l2-turboquant":
        raise AssertionError(f"new context did not preserve cache-response method: {context}")
    if message_count is not None and state.get("msgs") != message_count:
        raise AssertionError(f"message count mismatch after {action}: {state}")
    feed = state.get("feedRecent") or []
    if not any(action in entry.get("text", "") for entry in feed):
        raise AssertionError(f"chat control action {action} was not visible in activity feed: {feed}")
    return state


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-chat-control-actions")
        if seeded.get("ok") is not True:
            raise AssertionError(f"chat control seed failed: {seeded}")
        state = request("GET", "/state")
        if state.get("msgs", 0) < 1:
            raise AssertionError(f"seed did not create visible chat messages: {state}")

        response = request("POST", "/qa/chat-control-action", {"action": "setReasoning", "enabled": False})
        if response.get("ok") is not True:
            raise AssertionError(f"reasoning off action failed: {response}")
        assert_control("setReasoning", reasoning=False, inspector=False, generation=0)

        response = request("POST", "/qa/chat-control-action", {"action": "toggleContextInspector"})
        if response.get("ok") is not True:
            raise AssertionError(f"context inspector action failed: {response}")
        assert_control("toggleContextInspector", reasoning=False, inspector=True, generation=0)

        response = request("POST", "/qa/chat-control-action", {"action": "startNewContext"})
        if response.get("ok") is not True:
            raise AssertionError(f"new context action failed: {response}")
        assert_control("startNewContext", reasoning=False, inspector=False, generation=1, message_count=0)

        print("chat-control-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"chat-control-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
