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


EXPECTED_FAMILIES = {
    "recon": "nmap",
    "web": "nuclei",
    "network": "netexec",
    "creds": "hashcat",
    "exploit": "metasploit",
    "post": "linpeas",
    "osint": "gowitness",
}


def request(method: str, path: str, body: dict | str | None = None, timeout: float = 8.0):
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
    with tempfile.TemporaryDirectory(prefix="exploitbot-family-fanout-home-") as home:
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = home
        env["EXPLOITBOT_DATA_DIR"] = str(Path(home) / ".exploitbot" / "data")
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

        try:
            if app.wait(timeout=30) != 0:
                raise RuntimeError("build_and_run --verify failed")
            wait_for_app()

            seeded = request("POST", "/qa/seed-tool-family-fanout-fixture")
            if seeded.get("ok") is not True:
                raise AssertionError(f"tool family fanout seed failed: {seeded}")

            coverage = request("GET", "/qa/tool-family-fanout-coverage")
            failures = coverage.get("failures") or []
            if failures:
                raise AssertionError(f"tool family fanout coverage failures: {failures}")

            families = coverage.get("families") or {}
            if set(families) != set(EXPECTED_FAMILIES):
                raise AssertionError(f"unexpected family coverage set: {coverage}")
            for family, tool in EXPECTED_FAMILIES.items():
                item = families.get(family) or {}
                if item.get("tool") != tool:
                    raise AssertionError(f"{family} used wrong representative tool: {item}")
                for key in ("chatCard", "activityEntry", "tabActivity", "tabResult", "contextCatalog"):
                    if item.get(key) is not True:
                        raise AssertionError(f"{family} missing {key}: {item}")

            messages = request("GET", "/messages")
            tool_cards = {m.get("tool") for m in messages if m.get("tool")}
            missing_cards = set(EXPECTED_FAMILIES.values()).difference(tool_cards)
            if missing_cards:
                raise AssertionError(f"/messages missing representative tool cards {missing_cards}: {messages}")

            state = request("GET", "/state")
            activities = state.get("tabActivities") or {}
            for family, tool in EXPECTED_FAMILIES.items():
                activity = activities.get(family) or {}
                if activity.get("lastTool") != tool or activity.get("status") != "done":
                    raise AssertionError(f"/state tab activity missing {family}/{tool}: {activity}")
            recent_tools = {entry.get("tool") for entry in state.get("feedRecent", [])}
            if not set(EXPECTED_FAMILIES.values()).issubset(recent_tools):
                raise AssertionError(f"/state.feedRecent missing family tools: {state.get('feedRecent')}")

            print("tool-family-fanout-coverage proof passed")
        finally:
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if app.poll() is None:
                app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"tool-family-fanout-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
