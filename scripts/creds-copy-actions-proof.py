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


def assert_copy(kind: str, expected_count: int, expected_preview: str) -> None:
    copied = request("POST", "/qa/creds-copy", kind)
    if copied.get("ok") is not True:
        raise AssertionError(f"creds copy route failed for {kind}: {copied}")

    state = request("GET", "/state")
    action = state.get("credsCopyActions") or {}
    if action.get("status") != "copied" or action.get("kind") != kind:
        raise AssertionError(f"creds copy state missing for {kind}: {action}")
    if action.get("count") != expected_count:
        raise AssertionError(f"creds copy count wrong for {kind}: {action}")
    if expected_preview not in action.get("clipboardPreview", ""):
        raise AssertionError(f"creds copy preview wrong for {kind}: {action}")

    tab = state.get("tabActivities", {}).get("creds", {})
    if tab.get("status") != "done" or tab.get("lastTool") != "copy_creds":
        raise AssertionError(f"creds tab activity did not reflect copy for {kind}: {tab}")
    if kind not in tab.get("summary", ""):
        raise AssertionError(f"creds tab copy summary missing kind for {kind}: {tab}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-creds-copy-actions")
        if seeded.get("ok") is not True:
            raise AssertionError(f"creds copy seed failed: {seeded}")

        assert_copy("cracking", 2, "administrator")
        assert_copy("bruteforce", 1, "hydra")
        assert_copy("secrets", 1, "AWS_ACCESS_KEY_ID")
        assert_copy("vault", 4, "svc-backup")

        print("creds-copy-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"creds-copy-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
