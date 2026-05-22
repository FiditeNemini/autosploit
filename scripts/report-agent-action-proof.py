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

        seeded = request("POST", "/qa/seed-report-agent-action")
        if seeded.get("ok") is not True:
            raise AssertionError(f"report agent seed failed: {seeded}")

        state = request("GET", "/state")
        report_action = state.get("reportAction") or {}
        if report_action.get("kind") != "agentDraft":
            raise AssertionError(f"report action kind missing: {state}")
        if report_action.get("status") != "queued":
            raise AssertionError(f"report action status missing: {report_action}")
        if report_action.get("findingCount") != 1:
            raise AssertionError(f"report action finding count missing: {report_action}")
        if report_action.get("template") != "Full Pentest Report":
            raise AssertionError(f"report action template missing: {report_action}")
        prompt = report_action.get("prompt", "")
        for marker in ("Draft a penetration test report", "QA Report Agent Critical", "CVE-2021-41773"):
            if marker not in prompt:
                raise AssertionError(f"report action prompt missing {marker!r}: {report_action}")
        activity = state.get("tabActivities", {}).get("report", {})
        if activity.get("status") != "running" or activity.get("lastTool") != "agent_report":
            raise AssertionError(f"report tab activity did not expose agent draft progress: {state}")

        print("report-agent-action proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"report-agent-action proof failed: {exc}", flush=True)
        raise SystemExit(1)
