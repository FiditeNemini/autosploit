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


def assert_web_action(action: str, expected_preview: str) -> dict:
    response = request("POST", "/qa/web-row-action", action)
    if response.get("ok") is not True:
        raise AssertionError(f"web row action failed for {action}: {response}")

    state = request("GET", "/state")
    actions = state.get("webDirectActions") or {}
    if actions.get("lastAction") != action or actions.get("status") != "done":
        raise AssertionError(f"web row action state mismatch for {action}: {actions}")
    if expected_preview not in actions.get("clipboardPreview", "") and expected_preview not in actions.get("lastStashPreview", ""):
        raise AssertionError(f"web row action preview wrong for {action}: {actions}")
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

        seeded = request("POST", "/qa/seed-web-direct-actions")
        if seeded.get("ok") is not True:
            raise AssertionError(f"web row action seed failed: {seeded}")

        assert_web_action("copyTitle", "Apache 2.4.49 Path Traversal")
        assert_web_action("copyTarget", "http://apache-direct.test")
        assert_web_action("copyDetails", "CVE-2021-41773")
        state = assert_web_action("contextStash", "Apache 2.4.49 Path Traversal")

        stash = state.get("stashActions") or {}
        if stash.get("lastAction") != "add" or "Apache 2.4.49 Path Traversal" not in stash.get("clipboardPreview", ""):
            raise AssertionError(f"web context stash did not update stash state: {stash}")

        print("web-row-context-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"web-row-context-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
