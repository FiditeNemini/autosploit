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

        seeded = request("POST", "/qa/seed-web-verify-action")
        if seeded.get("ok") is not True:
            raise AssertionError(f"web verify seed failed: {seeded}")

        state = request("GET", "/state")
        action = state.get("webAction") or {}
        if action.get("kind") != "verify" or action.get("status") != "queued":
            raise AssertionError(f"verify action state missing: {state}")
        if action.get("target") != "http://apache-verify.test":
            raise AssertionError(f"verify target not tracked: {action}")
        if "Apache 2.4.49 Path Traversal" not in action.get("title", ""):
            raise AssertionError(f"verify finding title not tracked: {action}")
        if "minimal safe probes" not in action.get("prompt", ""):
            raise AssertionError(f"verify prompt not preserved: {action}")
        web_activity = state.get("tabActivities", {}).get("web", {})
        if web_activity.get("status") != "running" or web_activity.get("lastTool") != "verify":
            raise AssertionError(f"web tab activity did not expose verify progress: {state}")
        cve_rows = state.get("webCVERows") or []
        if len(cve_rows) != 1:
            raise AssertionError(f"expected one CVE row progress record: {state}")
        cve_row = cve_rows[0]
        if cve_row.get("cve") != "CVE-2021-41773":
            raise AssertionError(f"CVE row id not tracked: {cve_row}")
        if cve_row.get("status") != "verifying":
            raise AssertionError(f"CVE row progress did not mirror active verification: {cve_row}")
        if cve_row.get("hasDetails") is not True:
            raise AssertionError(f"CVE row enrichment status missing: {cve_row}")
        if cve_row.get("progressLabel") != "CVE verifying":
            raise AssertionError(f"CVE row visible progress label missing: {cve_row}")

        print("web-verify-action proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"web-verify-action proof failed: {exc}", flush=True)
        raise SystemExit(1)
