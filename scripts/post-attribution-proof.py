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

        seeded = request("POST", "/qa/seed-post-attribution")
        if seeded.get("ok") is not True:
            raise AssertionError(f"post attribution seed failed: {seeded}")

        state = request("GET", "/state")
        attribution = state.get("postAttribution") or []
        if len(attribution) < 3:
            raise AssertionError(f"expected linpeas/impacket/metasploit attribution rows: {state}")

        labels = {row.get("label"): row for row in attribution}
        if labels.get("linpeas-host", {}).get("host") != "qa-linux-01":
            raise AssertionError(f"linpeas host attribution missing: {attribution}")
        if labels.get("impacket-secretsdump", {}).get("host") != "192.0.2.55":
            raise AssertionError(f"impacket host attribution missing: {attribution}")
        if labels.get("metasploit-session", {}).get("sessionId") != "3":
            raise AssertionError(f"metasploit session attribution missing: {attribution}")
        if labels.get("metasploit-session", {}).get("host") != "192.0.2.77":
            raise AssertionError(f"metasploit session host attribution missing: {attribution}")

        results = request("GET", "/results")
        if len(results.get("postAttribution") or []) < 3:
            raise AssertionError(f"/results did not expose post attribution rows: {results}")

        print("post-attribution proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"post-attribution proof failed: {exc}", flush=True)
        raise SystemExit(1)
