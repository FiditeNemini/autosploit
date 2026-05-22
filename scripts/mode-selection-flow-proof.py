#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
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


def assert_modes(selection: dict) -> None:
    modes = selection.get("availableModes") or []
    if modes != ["autopilot", "copilot", "manual"]:
        raise AssertionError(f"mode list/order mismatch: {selection}")
    labels = selection.get("availableLabels") or []
    if labels != ["Autopilot", "Copilot", "Manual"]:
        raise AssertionError(f"mode labels mismatch: {selection}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        with tempfile.TemporaryDirectory(prefix="exploitbot-qwen-mode-") as tmp:
            model = Path(tmp)
            (model / "config.json").write_text('{"model_type":"qwen3_next"}\n', encoding="utf-8")
            onboarded = request("POST", "/qa/onboarding-complete", {
                "language": "en",
                "modelPath": str(model),
                "opName": "QA Manual Onboarded Op",
                "mode": "manual",
                "scope": "192.0.2.0/24",
                "startEngine": False,
            })
            if onboarded.get("ok") is not True:
                raise AssertionError(f"onboarding completion failed: {onboarded}")

        state = request("GET", "/state")
        selection = state.get("modeSelection") or {}
        assert_modes(selection)
        if state.get("mode") != "manual" or selection.get("activeOpMode") != "manual":
            raise AssertionError(f"onboarding did not apply manual mode: {state}")
        if selection.get("source") != "onboarding" or selection.get("lastAction") != "complete-onboarding":
            raise AssertionError(f"onboarding mode source missing: {selection}")
        if selection.get("showOnboarding") is not False:
            raise AssertionError(f"onboarding was not dismissed: {selection}")

        seeded = request("POST", "/qa/seed-pending-approval")
        if seeded.get("ok") is not True:
            raise AssertionError(f"pending approval seed failed: {seeded}")
        state = request("GET", "/state")
        if not (state.get("modeSelection") or {}).get("pendingApprovalVisible"):
            raise AssertionError(f"pending approval was not seeded: {state}")

        switched = request("POST", "/qa/sidebar-mode", "autopilot")
        if switched.get("ok") is not True:
            raise AssertionError(f"sidebar mode switch failed: {switched}")
        state = request("GET", "/state")
        selection = state.get("modeSelection") or {}
        assert_modes(selection)
        if state.get("mode") != "autopilot" or selection.get("activeOpMode") != "autopilot":
            raise AssertionError(f"sidebar mode did not persist to active op: {state}")
        if selection.get("source") != "sidebar" or selection.get("lastAction") != "select-mode":
            raise AssertionError(f"sidebar mode source missing: {selection}")
        if selection.get("pendingApprovalVisible") is not False or selection.get("pendingApprovalRejected") is not True:
            raise AssertionError(f"sidebar switch did not reject pending approval: {selection}")
        activity = state.get("feedRecent") or []
        if not any("mode" in entry.get("text", "").lower() for entry in activity):
            raise AssertionError(f"mode switch was not reflected in activity feed: {activity}")

        print("mode-selection-flow proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"mode-selection-flow proof failed: {exc}", flush=True)
        raise SystemExit(1)
