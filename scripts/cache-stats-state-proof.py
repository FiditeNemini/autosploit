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


def assert_cache_stats_state() -> None:
    state = request("GET", "/state")
    stats = state.get("engineCacheStats")
    if not stats:
        raise AssertionError(f"missing engineCacheStats in /state: {state}")
    if stats.get("turboQuantEnabled") is not True:
        raise AssertionError(f"missing TurboQuant enabled state: {stats}")
    if stats.get("turboQuantMakeCache") != "turboquant-q4 encode/decode":
        raise AssertionError(f"missing TurboQuant encode/decode marker: {stats}")
    if stats.get("promptL2Hits") != 12 or stats.get("promptL2Entries") != 18:
        raise AssertionError(f"missing prompt L2 counters: {stats}")
    if stats.get("blockL2Hits") != 41 or stats.get("blockL2Blocks") != 96:
        raise AssertionError(f"missing block L2 counters: {stats}")
    if stats.get("ssmDiskEnabled") is not True or stats.get("ssmDiskEntries") != 64:
        raise AssertionError(f"missing SSM companion disk counters: {stats}")
    if stats.get("memoryCacheMB") != 8192.0:
        raise AssertionError(f"missing cache memory counter: {stats}")


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
            raise AssertionError(f"settings visual seed failed: {seeded}")
        assert_cache_stats_state()
        print("cache-stats-state proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"cache-stats-state proof failed: {exc}", flush=True)
        raise SystemExit(1)
