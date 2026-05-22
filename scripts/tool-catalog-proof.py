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


def names_for(tab: str, query: str) -> list[str]:
    payload = request("POST", "/qa/tool-catalog", {"tab": tab, "query": query})
    return payload["toolNames"]


def assert_contains(values: list[str], expected: str, label: str) -> None:
    if expected not in values:
        raise AssertionError(f"{label} missing {expected!r}: {values}")


def assert_not_contains(values: list[str], unexpected: str, label: str) -> None:
    if unexpected in values:
        raise AssertionError(f"{label} included unrelated {unexpected!r}: {values}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        web_tools = names_for("web", "test Apache 2.4.49 path traversal with nuclei then sqlmap")
        assert_contains(web_tools, "search_context", "web catalogue")
        assert_contains(web_tools, "search_cve", "web catalogue")
        assert_contains(web_tools, "nuclei", "web catalogue")
        assert_contains(web_tools, "sqlmap", "web catalogue")
        assert_not_contains(web_tools, "sherlock", "web catalogue")
        assert_not_contains(web_tools, "sliver", "web catalogue")
        if len(web_tools) > 12:
            raise AssertionError(f"web catalogue is too broad: {web_tools}")

        osint_tools = names_for("osint", "check username and email exposure")
        assert_contains(osint_tools, "search_context", "osint catalogue")
        assert_contains(osint_tools, "sherlock", "osint catalogue")
        assert_contains(osint_tools, "holehe", "osint catalogue")
        assert_not_contains(osint_tools, "sqlmap", "osint catalogue")
        assert_not_contains(osint_tools, "metasploit", "osint catalogue")
        if len(osint_tools) > 12:
            raise AssertionError(f"osint catalogue is too broad: {osint_tools}")

        print("tool-catalog proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"tool-catalog proof failed: {exc}", flush=True)
        raise SystemExit(1)
