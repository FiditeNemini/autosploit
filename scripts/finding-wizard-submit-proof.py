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

        seeded = request("POST", "/qa/seed-window-overlay-actions")
        if seeded.get("ok") is not True:
            raise AssertionError(f"wizard submit seed failed: {seeded}")

        opened = request("POST", "/qa/window-overlay-action", {"action": "openFindingWizard"})
        if opened.get("ok") is not True:
            raise AssertionError(f"open wizard action failed: {opened}")

        submitted = request("POST", "/qa/finding-wizard-submit", {
            "title": "QA modal submitted finding",
            "vulnType": "path_traversal",
            "severity": "critical",
            "cvss": 9.8,
            "target": "http://wizard-submit.test",
            "description": "Modal submit proof finding",
            "impact": "Proof impact",
            "remediation": "Proof remediation",
            "cveId": "CVE-2021-41773",
        })
        if submitted.get("ok") is not True:
            raise AssertionError(f"wizard submit failed: {submitted}")

        state = request("GET", "/state")
        if state.get("findings") != 1:
            raise AssertionError(f"wizard submit did not create exactly one finding: {state}")
        actions = state.get("reportFindingActions") or {}
        if actions.get("lastAction") != "wizard-created" or actions.get("status") != "done":
            raise AssertionError(f"wizard submit action state missing: {actions}")
        if actions.get("wizardVisible") is not False:
            raise AssertionError(f"wizard was not dismissed after submit: {actions}")
        if not actions.get("lastCreatedId"):
            raise AssertionError(f"wizard submit did not expose created id: {actions}")
        feed = state.get("feedRecent") or []
        if not any("wizard-created" in entry.get("text", "") for entry in feed):
            raise AssertionError(f"wizard submit not visible in activity feed: {feed}")

        print("finding-wizard-submit proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"finding-wizard-submit proof failed: {exc}", flush=True)
        raise SystemExit(1)
