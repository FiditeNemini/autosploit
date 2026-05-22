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

        seeded = request("POST", "/qa/seed-recon-action-status")
        if seeded.get("ok") is not True:
            raise AssertionError(f"recon action seed failed: {seeded}")

        state = request("GET", "/state")
        action = state.get("reconAction") or {}
        if action.get("kind") != "fullRecon" or action.get("status") != "running":
            raise AssertionError(f"recon action state missing: {state}")
        if action.get("target") != "example.test":
            raise AssertionError(f"recon target not tracked: {action}")
        if "subfinder" not in action.get("command", "") or "nmap" not in action.get("command", ""):
            raise AssertionError(f"recon command not preserved: {action}")
        tab = state.get("tabActivities", {}).get("recon", {})
        if tab.get("status") != "running" or tab.get("lastTool") != "full_recon":
            raise AssertionError(f"recon tab activity did not expose action progress: {state}")

        print("recon-action-status proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"recon-action-status proof failed: {exc}", flush=True)
        raise SystemExit(1)
