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


def assert_window_action(action: str, *, terminal: bool, settings: bool, wizard: bool) -> None:
    state = request("GET", "/state")
    window = state.get("windowOverlayActions") or {}
    if window.get("lastAction") != action or window.get("status") != "done":
        raise AssertionError(f"window overlay action missing for {action}: {window}")
    if window.get("terminalVisible") is not terminal:
        raise AssertionError(f"terminal visibility mismatch after {action}: {window}")
    if window.get("settingsVisible") is not settings:
        raise AssertionError(f"settings visibility mismatch after {action}: {window}")
    if window.get("findingWizardVisible") is not wizard:
        raise AssertionError(f"wizard visibility mismatch after {action}: {window}")
    feed = state.get("feedRecent") or []
    if not any(action in entry.get("text", "") for entry in feed):
        raise AssertionError(f"window overlay action {action} was not visible in activity feed: {feed}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-window-overlay-actions")
        if seeded.get("ok") is not True:
            raise AssertionError(f"window overlay seed failed: {seeded}")

        request("POST", "/qa/window-overlay-action", {"action": "toggleTerminal"})
        assert_window_action("toggleTerminal", terminal=True, settings=False, wizard=False)

        request("POST", "/qa/window-overlay-action", {"action": "closeTerminal"})
        assert_window_action("closeTerminal", terminal=False, settings=False, wizard=False)

        request("POST", "/qa/window-overlay-action", {"action": "openSettings"})
        assert_window_action("openSettings", terminal=False, settings=True, wizard=False)

        request("POST", "/qa/window-overlay-action", {"action": "closeSettings"})
        assert_window_action("closeSettings", terminal=False, settings=False, wizard=False)

        request("POST", "/qa/window-overlay-action", {"action": "openFindingWizard"})
        assert_window_action("openFindingWizard", terminal=False, settings=False, wizard=True)

        request("POST", "/qa/window-overlay-action", {"action": "dismissFindingWizard"})
        assert_window_action("dismissFindingWizard", terminal=False, settings=False, wizard=False)

        print("window-overlay-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"window-overlay-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
