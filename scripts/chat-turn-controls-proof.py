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


def assert_control(action: str, *, message_count: int | None = None, pending: bool | None = None) -> dict:
    state = request("GET", "/state")
    control = state.get("chatControlActions") or {}
    if control.get("lastAction") != action or control.get("status") != "done":
        raise AssertionError(f"chat turn control action missing for {action}: {control}")
    if message_count is not None and state.get("msgs") != message_count:
        raise AssertionError(f"message count mismatch after {action}: {state}")
    selection = state.get("modeSelection") or {}
    if pending is not None and selection.get("pendingApprovalVisible") is not pending:
        raise AssertionError(f"pending approval visibility mismatch after {action}: {selection}")
    feed = state.get("feedRecent") or []
    if not any(action in entry.get("text", "") for entry in feed):
        raise AssertionError(f"chat turn control action {action} was not visible in activity feed: {feed}")
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

        sent = request("POST", "/qa/chat-control-action", {"action": "send", "text": "QA turn-control message"})
        if sent.get("ok") is not True:
            raise AssertionError(f"send action failed: {sent}")
        assert_control("send", message_count=4)

        stopped = request("POST", "/qa/chat-control-action", {"action": "stop"})
        if stopped.get("ok") is not True:
            raise AssertionError(f"stop action failed: {stopped}")
        assert_control("stop")

        seeded_approval = request("POST", "/qa/seed-pending-approval")
        if seeded_approval.get("ok") is not True:
            raise AssertionError(f"pending approval seed failed: {seeded_approval}")
        approved = request("POST", "/qa/chat-control-action", {"action": "approve"})
        if approved.get("ok") is not True:
            raise AssertionError(f"approval action failed: {approved}")
        assert_control("approve", pending=False)

        seeded_approval = request("POST", "/qa/seed-pending-approval")
        if seeded_approval.get("ok") is not True:
            raise AssertionError(f"pending approval seed failed: {seeded_approval}")
        rejected = request("POST", "/qa/chat-control-action", {"action": "reject"})
        if rejected.get("ok") is not True:
            raise AssertionError(f"rejection action failed: {rejected}")
        assert_control("reject", pending=False)

        print("chat-turn-controls proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"chat-turn-controls proof failed: {exc}", flush=True)
        raise SystemExit(1)
