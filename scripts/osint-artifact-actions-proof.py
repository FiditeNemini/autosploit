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


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-osint-screenshot-artifact")
        if seeded.get("ok") is not True:
            raise AssertionError(f"osint screenshot artifact seed failed: {seeded}")

        revealed = request("POST", "/qa/osint-artifact-action", "reveal")
        if revealed.get("ok") is not True:
            raise AssertionError(f"reveal action failed: {revealed}")
        opened = request("POST", "/qa/osint-artifact-action", "open")
        if opened.get("ok") is not True:
            raise AssertionError(f"open action failed: {opened}")

        state = request("GET", "/state")
        action = state.get("osintArtifactAction") or {}
        if action.get("lastAction") != "open":
            raise AssertionError(f"last artifact action was not tracked: {state}")
        if action.get("status") != "done" or action.get("summary") != "opened artifact":
            raise AssertionError(f"artifact action status was not surfaced: {action}")
        if action.get("pathExists") is not True or action.get("bytes", 0) <= 0:
            raise AssertionError(f"artifact action did not validate file: {state}")
        history = action.get("history") or []
        if history != ["reveal", "open"]:
            raise AssertionError(f"artifact action history incorrect: {action}")
        actions = (state.get("osintArtifacts") or [{}])[0].get("actions") or []
        for expected in ("open", "reveal", "copyPath"):
            if expected not in actions:
                raise AssertionError(f"artifact row missing action {expected}: {state}")
        action_labels = (state.get("osintArtifacts") or [{}])[0].get("actionLabels") or {}
        expected_labels = {"open": "Open", "reveal": "Reveal", "copyPath": "Copy Path"}
        if action_labels != expected_labels:
            raise AssertionError(f"artifact row missing action labels: {state}")

        print("osint-artifact-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"osint-artifact-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
