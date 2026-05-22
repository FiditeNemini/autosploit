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

EXPECTED_CATEGORIES = [
    "engine",
    "model",
    "runtime",
    "context",
    "cache",
    "agents",
    "cves",
    "tools",
    "logs",
]


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

        seeded = request("POST", "/qa/seed-settings-visual-state")
        if seeded.get("ok") is not True:
            raise AssertionError(f"settings seed failed: {seeded}")

        state = request("GET", "/state")
        coverage = state.get("settingsCategoryCoverage") or {}
        if coverage.get("splitPages") is not True:
            raise AssertionError(f"settings categories are not exposed as split pages: {coverage}")

        categories = coverage.get("categories") or []
        ids = [item.get("id") for item in categories]
        if ids != EXPECTED_CATEGORIES:
            raise AssertionError(f"settings category order mismatch: {ids}")

        for item in categories:
            for key in ("id", "title", "subtitle", "detail", "systemImage", "pageSections"):
                if not item.get(key):
                    raise AssertionError(f"settings category missing {key}: {item}")
            if not isinstance(item.get("pageSections"), list):
                raise AssertionError(f"pageSections is not a list: {item}")

        for category in EXPECTED_CATEGORIES:
            switched = request("POST", "/qa/settings-category", category)
            if switched.get("ok") is not True or switched.get("category") != category:
                raise AssertionError(f"could not switch settings category {category}: {switched}")
            state = request("GET", "/state")
            if (state.get("qaSettingsVisual") or {}).get("category") != category:
                raise AssertionError(f"settings category state did not switch to {category}: {state}")

        print("settings-category-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"settings-category-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
