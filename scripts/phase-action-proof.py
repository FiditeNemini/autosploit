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


def assert_phase_action(expected_action: str, expected_from: str, expected_to: str) -> None:
    state = request("GET", "/state")
    phase = state.get("phaseActions") or {}
    if phase.get("status") != "done" or phase.get("lastAction") != expected_action:
        raise AssertionError(f"phase action state mismatch: {phase}")
    if phase.get("fromPhase") != expected_from or phase.get("toPhase") != expected_to:
        raise AssertionError(f"phase transition mismatch: {phase}")
    if state.get("phase") != expected_to:
        raise AssertionError(f"state phase did not update to {expected_to}: {state.get('phase')}")
    if phase.get("toolsRun") != 0:
        raise AssertionError(f"phase action did not reset tool counter: {phase}")
    if not phase.get("phaseGuidance"):
        raise AssertionError(f"phase action did not expose chat phase guidance: {phase}")
    feed = state.get("feedRecent") or []
    if not any(expected_action in entry.get("text", "") and expected_to in entry.get("text", "") for entry in feed):
        raise AssertionError(f"phase action missing from activity feed: {feed}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        advanced = request("POST", "/phase", "next")
        if advanced.get("ok") is not True:
            raise AssertionError(f"phase advance failed: {advanced}")
        assert_phase_action("advancePhase", "scan", "detect")

        set_breach = request("POST", "/phase", "breach")
        if set_breach.get("ok") is not True:
            raise AssertionError(f"phase set failed: {set_breach}")
        assert_phase_action("setPhase", "detect", "breach")

        print("phase-action proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"phase-action proof failed: {exc}", flush=True)
        raise SystemExit(1)
