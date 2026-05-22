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


def assert_chat_action(action: str, expected_count: int, expected_preview: str) -> dict:
    response = request("POST", "/qa/chat-action", action)
    if response.get("ok") is not True:
        raise AssertionError(f"chat action failed for {action}: {response}")

    state = request("GET", "/state")
    chat = state.get("chatActions") or {}
    if chat.get("status") != "done" or chat.get("lastAction") != action:
        raise AssertionError(f"chat action state missing for {action}: {chat}")
    if chat.get("count") != expected_count:
        raise AssertionError(f"chat action count wrong for {action}: {chat}")
    if expected_preview and expected_preview not in chat.get("clipboardPreview", ""):
        raise AssertionError(f"chat action preview wrong for {action}: {chat}")
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

        seeded = request("POST", "/qa/seed-chat-actions")
        if seeded.get("ok") is not True:
            raise AssertionError(f"chat action seed failed: {seeded}")

        state = assert_chat_action("copyTranscript", 4, "Assistant: QA assistant evidence")
        if (state.get("chatActions") or {}).get("messageRole") != "transcript":
            raise AssertionError(f"copy transcript did not mark transcript role: {state}")

        state = assert_chat_action("copyAssistant", 1, "QA assistant evidence")
        if (state.get("chatActions") or {}).get("messageRole") != "assistant":
            raise AssertionError(f"copy assistant did not mark message role: {state}")

        state = assert_chat_action("stashAssistant", 1, "QA assistant evidence")
        stash = state.get("stashActions") or {}
        if stash.get("lastAction") != "add" or "QA assistant evidence" not in stash.get("clipboardPreview", ""):
            raise AssertionError(f"chat stash did not route through stash action state: {stash}")

        state = assert_chat_action("stashLatestAssistant", 1, "QA final assistant note")
        stash = state.get("stashActions") or {}
        if stash.get("lastAction") != "add" or "QA final assistant note" not in stash.get("clipboardPreview", ""):
            raise AssertionError(f"latest assistant stash did not update stash state: {stash}")

        print("chat-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"chat-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
