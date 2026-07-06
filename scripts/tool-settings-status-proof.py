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

        seeded = request("POST", "/qa/seed-tool-settings-status")
        if seeded.get("ok") is not True:
            raise AssertionError(f"tool settings seed failed: {seeded}")

        state = request("GET", "/state")
        tool_settings = state.get("toolSettings") or {}
        expected = {
            "installedCount": 2,
            "missingCount": 2,
            "installingCount": 1,
            "errorCount": 1,
            "isInstalling": True,
            "activeSettingsCategory": "tools",
        }
        for key, value in expected.items():
            if tool_settings.get(key) != value:
                raise AssertionError(f"tool settings {key}={tool_settings.get(key)!r}; expected {value!r}: {state}")
        names = [tool.get("name") for tool in tool_settings.get("tools", [])]
        for expected_name in ("nmap", "httpx", "sqlmap", "hashcat", "sherlock", "syft"):
            if expected_name not in names:
                raise AssertionError(f"missing tool row {expected_name}: {tool_settings}")
        statuses = {tool.get("name"): tool.get("status") for tool in tool_settings.get("tools", [])}
        if statuses.get("httpx") != "installing" or statuses.get("hashcat") != "error":
            raise AssertionError(f"tool row statuses not exposed: {tool_settings}")
        if "QA tool install log" not in tool_settings.get("installLog", ""):
            raise AssertionError(f"install log missing: {tool_settings}")

        print("tool-settings-status proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"tool-settings-status proof failed: {exc}", flush=True)
        raise SystemExit(1)
