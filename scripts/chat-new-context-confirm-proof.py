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


def confirm_state(state: dict) -> dict:
    qa = state.get("qaChatVisual") or {}
    confirm = qa.get("newContextConfirm") or {}
    if not isinstance(confirm, dict):
        raise AssertionError(f"missing new context confirmation state: {qa}")
    return confirm


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
        before = request("GET", "/state")
        before_msgs = before.get("msgs")
        if not before_msgs:
            raise AssertionError(f"seed did not create messages: {before}")

        opened = request("POST", "/qa/chat-new-context-confirm", {"action": "open"})
        if opened.get("ok") is not True:
            raise AssertionError(f"open confirmation failed: {opened}")
        state = request("GET", "/state")
        confirm = confirm_state(state)
        if confirm.get("isVisible") is not True or confirm.get("lastAction") != "openNewContextConfirm":
            raise AssertionError(f"confirmation open state wrong: {confirm}")
        if state.get("msgs") != before_msgs:
            raise AssertionError(f"opening confirmation changed messages: {state}")

        cancelled = request("POST", "/qa/chat-new-context-confirm", {"action": "cancel"})
        if cancelled.get("ok") is not True:
            raise AssertionError(f"cancel confirmation failed: {cancelled}")
        state = request("GET", "/state")
        confirm = confirm_state(state)
        if confirm.get("isVisible") is not False or confirm.get("lastAction") != "cancelNewContextConfirm":
            raise AssertionError(f"confirmation cancel state wrong: {confirm}")
        if state.get("msgs") != before_msgs:
            raise AssertionError(f"cancelling confirmation changed messages: {state}")

        request("POST", "/qa/chat-new-context-confirm", {"action": "open"})
        confirmed = request("POST", "/qa/chat-new-context-confirm", {"action": "confirm"})
        if confirmed.get("ok") is not True:
            raise AssertionError(f"confirm new context failed: {confirmed}")
        state = request("GET", "/state")
        confirm = confirm_state(state)
        if confirm.get("isVisible") is not False or confirm.get("lastAction") != "confirmNewContext":
            raise AssertionError(f"confirmation final state wrong: {confirm}")
        if state.get("msgs") != 0:
            raise AssertionError(f"confirm did not clear chat messages: {state}")
        context = state.get("contextWindow") or {}
        if context.get("cacheResponsesMethod") != "prefix-cache-l2-turboquant":
            raise AssertionError(f"confirm did not preserve cache response method: {context}")
        if context.get("cacheResponsesInferenceMethod") != "prefix-cache-l2-turboquant":
            raise AssertionError(f"confirm did not preserve explicit cache inference method: {context}")
        if context.get("sessionBoundaryMode") != "new-context-window":
            raise AssertionError(f"confirm did not expose new context-window boundary: {context}")
        if context.get("newModelSessionBehavior") != "new-context-window-preserve-engine-cache-session":
            raise AssertionError(f"confirm did not expose new model session behavior: {context}")
        if context.get("engineSessionPreserved") is not True:
            raise AssertionError(f"confirm did not preserve engine session: {context}")

        feed = state.get("feedRecent") or []
        if not any("confirmNewContext" in entry.get("text", "") for entry in feed):
            raise AssertionError(f"confirm action not visible in activity feed: {feed}")

        print("chat-new-context-confirm proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"chat-new-context-confirm proof failed: {exc}", flush=True)
        raise SystemExit(1)
