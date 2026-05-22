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
MOCK_ENGINE = "http://127.0.0.1:18991"


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

        request("POST", "/engine/mock", MOCK_ENGINE)
        before = request("GET", "/state")
        request("POST", "/qa/apply-app-settings", {
            "maxIterations": 7,
            "context": {
                "enabled": True,
                "maxSnippets": 3,
                "includeAssets": False,
                "includeFindings": True,
                "includeRecentToolOutput": False,
                "includeStash": True,
                "cveMode": "current",
            },
            "agents": {
                "multiAgentEnabled": True,
                "maxConcurrentAgents": 8,
            },
        })
        after = request("GET", "/state")

        assert after["engineRunning"] == before["engineRunning"], (before, after)
        assert after["healthStatus"] == before["healthStatus"], (before, after)
        assert after["model"] == before["model"], (before, after)
        assert after["chat"]["maxIterations"] == 7, after
        assert after["contextCatalog"]["maxSnippets"] == 3, after
        assert after["contextCatalog"]["includeAssets"] is False, after
        assert after["contextCatalog"]["includeRecentToolOutput"] is False, after
        assert after["contextCatalog"]["includeFindings"] is True, after
        assert after["contextCatalog"]["includeStash"] is True, after
        assert after["contextCatalog"]["cveMode"] == "current", after
        assert after["agents"]["multiAgentEnabled"] is True, after
        assert after["agents"]["maxConcurrentAgents"] == 8, after

        print("settings-apply proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"settings-apply proof failed: {exc}", flush=True)
        raise SystemExit(1)
