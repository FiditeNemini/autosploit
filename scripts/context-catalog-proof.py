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


def assert_not_contains(haystack: str, needle: str, label: str) -> None:
    if needle in haystack:
        raise AssertionError(f"{label} leaked into context packet: {needle!r}\n{haystack}")


def assert_contains(haystack: str, needle: str, label: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"{label} missing from context packet: {needle!r}\n{haystack}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-context-scope")
        active_op = seeded["activeOpId"]

        disabled_packet = request("POST", "/qa/context-packet", {
            "query": "disabled source leakage",
            "maxSnippets": 10,
            "includeAssets": False,
            "includeFindings": False,
            "includeRecentToolOutput": False,
            "includeStash": False,
            "cveMode": "off",
        })["packet"]
        assert_not_contains(disabled_packet, "disabled-asset-service", "asset source")
        assert_not_contains(disabled_packet, "disabled-finding-title", "finding source")
        assert_not_contains(disabled_packet, "disabled recent output body", "recent output source")
        assert_not_contains(disabled_packet, "disabled-stash-label", "stash source")
        assert_contains(disabled_packet, "Selected snippets: none yet.", "empty selected state")

        scoped_packet = request("POST", "/qa/context-packet", {
            "query": "operation note",
            "maxSnippets": 10,
            "includeAssets": False,
            "includeFindings": False,
            "includeRecentToolOutput": False,
            "includeStash": True,
            "cveMode": "off",
            "activeOpId": active_op,
        })["packet"]
        assert_contains(scoped_packet, "active-op-note", "active op stash")
        assert_contains(scoped_packet, "global-note", "global stash")
        assert_not_contains(scoped_packet, "inactive-op-note", "inactive op stash")

        print("context-catalog proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"context-catalog proof failed: {exc}", flush=True)
        raise SystemExit(1)
