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
    with tempfile.TemporaryDirectory(prefix="exploitbot-parser-fanout-home-") as home:
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

            if request("POST", "/qa/seed-result-parser-fixture").get("ok") is not True:
                raise AssertionError("result parser seed failed")
            parser = request("GET", "/qa/result-parser-coverage")
            if parser.get("ok") is not True:
                raise AssertionError(f"result parser aggregate missing ok=true: {parser}")
            if parser.get("failures"):
                raise AssertionError(f"result parser failures: {parser}")
            if parser.get("counts", {}).get("rawResults", 0) < 35:
                raise AssertionError(f"result parser raw result count too low: {parser}")

            if request("POST", "/qa/seed-tool-family-fanout-fixture").get("ok") is not True:
                raise AssertionError("tool family fanout seed failed")
            fanout = request("GET", "/qa/tool-family-fanout-coverage")
            if fanout.get("ok") is not True:
                raise AssertionError(f"tool family fanout aggregate missing ok=true: {fanout}")
            if fanout.get("failures"):
                raise AssertionError(f"tool family fanout failures: {fanout}")
            if sorted((fanout.get("families") or {}).keys()) != ["creds", "exploit", "network", "osint", "post", "recon", "report", "stash", "supplyChain", "web"]:
                raise AssertionError(f"tool family fanout family set mismatch: {fanout}")

            print("parser-fanout-aggregate proof passed")
        finally:
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if app.poll() is None:
                app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"parser-fanout-aggregate proof failed: {exc}", flush=True)
        raise SystemExit(1)
