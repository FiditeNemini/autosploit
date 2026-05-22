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

        seeded = request("POST", "/qa/seed-osint-screenshot-artifact")
        if seeded.get("ok") is not True:
            raise AssertionError(f"osint screenshot artifact seed failed: {seeded}")

        state = request("GET", "/state")
        artifacts = state.get("osintArtifacts") or []
        if len(artifacts) != 1:
            raise AssertionError(f"expected exactly one OSINT artifact: {state}")
        artifact = artifacts[0]
        if artifact.get("platform") != "Screenshot" or artifact.get("found") is not True:
            raise AssertionError(f"unexpected screenshot artifact row: {artifact}")
        if artifact.get("exists") is not True or artifact.get("bytes", 0) <= 0:
            raise AssertionError(f"screenshot artifact file was not validated: {artifact}")
        if artifact.get("previewKind") != "image":
            raise AssertionError(f"screenshot artifact should expose image preview kind: {artifact}")
        lifecycle = state.get("osintLifecycle", {}).get("screenshot", {})
        if lifecycle.get("status") != "done" or lifecycle.get("tool") != "gowitness":
            raise AssertionError(f"screenshot lifecycle did not complete: {state}")

        results = request("GET", "/results")
        osint = results.get("osint") or []
        if not osint or osint[0].get("previewKind") != "image":
            raise AssertionError(f"/results did not expose screenshot preview metadata: {results}")

        print("osint-screenshot-artifact proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"osint-screenshot-artifact proof failed: {exc}", flush=True)
        raise SystemExit(1)
