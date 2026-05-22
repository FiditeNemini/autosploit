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

        seeded = request("POST", "/qa/seed-creds-action-results")
        if seeded.get("ok") is not True:
            raise AssertionError(f"creds action seed failed: {seeded}")

        state = request("GET", "/state")
        action = state.get("credsAction") or {}
        if action.get("kind") != "crack" or action.get("status") != "done":
            raise AssertionError(f"creds action state missing: {state}")
        if action.get("target") != "qa.hashes":
            raise AssertionError(f"creds target not tracked: {action}")
        if "hashcat" not in action.get("command", "") or "haiti" not in action.get("command", ""):
            raise AssertionError(f"creds command did not preserve crack plan: {action}")
        if action.get("resultCount") != 2:
            raise AssertionError(f"creds action did not count cracked results: {action}")

        tab = state.get("tabActivities", {}).get("creds", {})
        if tab.get("status") != "done" or tab.get("lastTool") != "hashcat":
            raise AssertionError(f"creds tab activity did not expose done state: {state}")

        results = request("GET", "/results").get("creds", [])
        if len(results) != 2:
            raise AssertionError(f"expected two credential result rows: {results}")
        labels = {row.get("label") for row in results}
        badges = {row.get("badge") for row in results}
        if "administrator" not in labels or "svc-backup" not in labels:
            raise AssertionError(f"credential labels missing: {results}")
        if badges != {"CRACKED"}:
            raise AssertionError(f"credential badges missing: {results}")

        print("creds-action-results proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"creds-action-results proof failed: {exc}", flush=True)
        raise SystemExit(1)
