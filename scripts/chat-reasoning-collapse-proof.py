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


def assert_reasoning(state: dict, *, collapsed: bool, visible_chars: int) -> None:
    qa = state.get("qaChatVisual") or {}
    reasoning = qa.get("reasoningBlock") or {}
    if reasoning.get("isCollapsed") is not collapsed:
        raise AssertionError(f"reasoning collapse state mismatch: {reasoning}")
    if reasoning.get("visibleChars") != visible_chars:
        raise AssertionError(f"reasoning visible char count mismatch: {reasoning}")
    if reasoning.get("totalChars", 0) <= 0:
        raise AssertionError(f"reasoning total chars missing: {reasoning}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-chat-reasoning-collapse")
        if seeded.get("ok") is not True:
            raise AssertionError(f"chat reasoning seed failed: {seeded}")
        state = request("GET", "/state")
        total = ((state.get("qaChatVisual") or {}).get("reasoningBlock") or {}).get("totalChars", 0)
        assert_reasoning(state, collapsed=False, visible_chars=total)

        collapsed = request("POST", "/qa/chat-reasoning-collapse", {"collapsed": True})
        if collapsed.get("ok") is not True:
            raise AssertionError(f"chat reasoning collapse failed: {collapsed}")
        state = request("GET", "/state")
        assert_reasoning(state, collapsed=True, visible_chars=0)

        expanded = request("POST", "/qa/chat-reasoning-collapse", {"collapsed": False})
        if expanded.get("ok") is not True:
            raise AssertionError(f"chat reasoning expand failed: {expanded}")
        state = request("GET", "/state")
        total = ((state.get("qaChatVisual") or {}).get("reasoningBlock") or {}).get("totalChars", 0)
        assert_reasoning(state, collapsed=False, visible_chars=total)

        feed = state.get("feedRecent") or []
        if not any("expandReasoningBlock" in entry.get("text", "") for entry in feed):
            raise AssertionError(f"reasoning expand not visible in activity feed: {feed}")

        print("chat-reasoning-collapse proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"chat-reasoning-collapse proof failed: {exc}", flush=True)
        raise SystemExit(1)

