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
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        switched = request("POST", "/qa/tool-subtab", {"tab": "creds", "subtab": "Secrets"})
        if switched.get("ok") is not True:
            raise AssertionError(f"creds subtab switch failed: {switched}")

        state = request("GET", "/state")
        active = state.get("activeSubtabs") or {}
        actions = state.get("subtabActions") or {}
        if active.get("creds") != "Secrets":
            raise AssertionError(f"creds active subtab missing from state: {active}")
        if actions.get("lastAction") != "selectSubtab" or actions.get("tab") != "creds" or actions.get("subtab") != "Secrets":
            raise AssertionError(f"creds subtab action state mismatch: {actions}")
        for label in ("Cracking", "Online Brute", "Secrets", "Vault"):
            if label not in actions.get("validSubtabs", []):
                raise AssertionError(f"creds valid subtabs missing {label}: {actions}")
        if state.get("activeTab") != "creds":
            raise AssertionError(f"subtab switch did not activate creds tab: {state.get('activeTab')}")

        bad = request("POST", "/qa/tool-subtab", {"tab": "creds", "subtab": "MadeUp"})
        if bad.get("ok") is not False:
            raise AssertionError(f"bad creds subtab should be rejected: {bad}")

        print("creds-subtab-state proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"creds-subtab-state proof failed: {exc}", flush=True)
        raise SystemExit(1)
