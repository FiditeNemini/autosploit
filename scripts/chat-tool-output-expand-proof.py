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


def assert_tool_expand(state: dict, *, expanded: bool, visible_lines: int, hidden_lines: int) -> None:
    qa = state.get("qaChatVisual") or {}
    tool = qa.get("toolOutputExpansion") or {}
    if tool.get("toolName") != "long_tool":
        raise AssertionError(f"wrong tool expansion target: {tool}")
    if tool.get("isExpanded") is not expanded:
        raise AssertionError(f"tool expansion state mismatch: {tool}")
    if tool.get("visibleLineCount") != visible_lines:
        raise AssertionError(f"visible line count mismatch: {tool}")
    if tool.get("hiddenLineCount") != hidden_lines:
        raise AssertionError(f"hidden line count mismatch: {tool}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-chat-tool-output-expand")
        if seeded.get("ok") is not True:
            raise AssertionError(f"chat tool-output seed failed: {seeded}")

        state = request("GET", "/state")
        assert_tool_expand(state, expanded=False, visible_lines=5, hidden_lines=7)

        toggled = request("POST", "/qa/chat-tool-output-expand", {"expanded": True})
        if toggled.get("ok") is not True:
            raise AssertionError(f"chat tool-output expand failed: {toggled}")
        state = request("GET", "/state")
        assert_tool_expand(state, expanded=True, visible_lines=12, hidden_lines=0)

        toggled = request("POST", "/qa/chat-tool-output-expand", {"expanded": False})
        if toggled.get("ok") is not True:
            raise AssertionError(f"chat tool-output collapse failed: {toggled}")
        state = request("GET", "/state")
        assert_tool_expand(state, expanded=False, visible_lines=5, hidden_lines=7)

        feed = state.get("feedRecent") or []
        if not any("collapseToolOutput" in entry.get("text", "") for entry in feed):
            raise AssertionError(f"tool-output collapse not visible in activity feed: {feed}")

        print("chat-tool-output-expand proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"chat-tool-output-expand proof failed: {exc}", flush=True)
        raise SystemExit(1)

