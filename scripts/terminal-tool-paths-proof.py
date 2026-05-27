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


def run() -> None:
    content = (ROOT / "ExploitBot" / "Sources" / "ExploitBot" / "Views" / "ContentView.swift").read_text()
    if "toolPaths: state.terminalToolPaths" not in content:
        raise AssertionError("TerminalPanelView is not wired to AppState terminalToolPaths")

    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-tool-settings-status")
        if seeded.get("ok") is not True:
            raise AssertionError(f"tool settings seed failed: {seeded}")

        state = request("GET", "/state")
        terminal = state.get("terminal") or {}
        paths = terminal.get("toolPaths") or []
        if terminal.get("toolPathCount") != len(paths):
            raise AssertionError(f"terminal path count mismatch: {terminal}")
        if len(paths) != len(set(paths)):
            raise AssertionError(f"terminal tool paths are not deduplicated: {paths}")
        for expected in ("/opt/homebrew/bin", "/Users/eric/.local/bin"):
            if expected not in paths:
                raise AssertionError(f"terminal path missing {expected}: {terminal}")
        if terminal.get("installedToolCount", 0) < 2:
            raise AssertionError(f"terminal installed tool count too low: {terminal}")

        request("POST", "/qa/window-overlay-action", {"action": "toggleTerminal"})
        visible = request("GET", "/state").get("terminal") or {}
        if visible.get("isVisible") is not True:
            raise AssertionError(f"terminal visibility did not update in terminal state: {visible}")

        print("terminal-tool-paths proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"terminal-tool-paths proof failed: {exc}", flush=True)
        raise SystemExit(1)
