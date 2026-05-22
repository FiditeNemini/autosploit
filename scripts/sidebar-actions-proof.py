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


def assert_sidebar_action(action: str, expected_name: str, expected_count: int, expected_active: str) -> None:
    state = request("GET", "/state")
    sidebar = state.get("sidebarActions") or {}
    if sidebar.get("lastAction") != action or sidebar.get("status") != "done":
        raise AssertionError(f"sidebar action state missing for {action}: {sidebar}")
    if sidebar.get("opName") != expected_name:
        raise AssertionError(f"sidebar action op name wrong for {action}: {sidebar}")
    if sidebar.get("opsCount") != expected_count:
        raise AssertionError(f"sidebar op count wrong for {action}: {sidebar}")
    mode = state.get("modeSelection") or {}
    if mode.get("activeOpName") != expected_active:
        raise AssertionError(f"active op wrong after {action}: {mode}")
    feed = state.get("feedRecent") or []
    if not any(action.replace("Op", " op").replace("create", "created").split("Op")[0] in entry.get("text", "") for entry in feed):
        raise AssertionError(f"sidebar action {action} was not reflected in activity feed: {feed}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-sidebar-actions")
        if seeded.get("ok") is not True:
            raise AssertionError(f"sidebar action seed failed: {seeded}")

        state = request("GET", "/state")
        sidebar = state.get("sidebarActions") or {}
        if sidebar.get("opsCount") != 2:
            raise AssertionError(f"sidebar seed did not expose two ops: {state}")
        if (state.get("modeSelection") or {}).get("activeOpName") != "QA Sidebar Primary":
            raise AssertionError(f"sidebar seed active op mismatch: {state}")

        response = request("POST", "/qa/sidebar-action", {"action": "createOp", "name": "QA Sidebar New"})
        if response.get("ok") is not True:
            raise AssertionError(f"create op action failed: {response}")
        assert_sidebar_action("createOp", "QA Sidebar New", 3, "QA Sidebar New")

        response = request("POST", "/qa/sidebar-action", {"action": "renameOp", "name": "QA Sidebar Renamed"})
        if response.get("ok") is not True:
            raise AssertionError(f"rename op action failed: {response}")
        assert_sidebar_action("renameOp", "QA Sidebar Renamed", 3, "QA Sidebar Renamed")

        response = request("POST", "/qa/sidebar-action", {"action": "switchOp", "target": "secondary"})
        if response.get("ok") is not True:
            raise AssertionError(f"switch op action failed: {response}")
        assert_sidebar_action("switchOp", "QA Sidebar Secondary", 3, "QA Sidebar Secondary")

        response = request("POST", "/qa/sidebar-action", {"action": "deleteOp", "target": "active"})
        if response.get("ok") is not True:
            raise AssertionError(f"delete op action failed: {response}")
        assert_sidebar_action("deleteOp", "QA Sidebar Secondary", 2, "QA Sidebar Renamed")

        print("sidebar-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"sidebar-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
