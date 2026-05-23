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

EXPECTED_TABS = ["creds", "exploit", "network", "osint", "post", "recon", "report", "stash", "web"]
EXPECTED_CALLBACKS = ["lookup_cve", "search_context", "search_cve"]
EXPECTED_ALWAYS_VISIBLE = ["lookup_cve", "run_shell", "search_context", "search_cve"]


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
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        coverage = request("GET", "/qa/tool-coverage")
        tools = coverage.get("tools") or []
        if coverage.get("ok") is not True:
            raise AssertionError(f"tool coverage failed: {coverage}")
        if coverage.get("toolCount") != len(tools):
            raise AssertionError(f"tool count does not match detail rows: {coverage}")
        if coverage.get("tabs") != EXPECTED_TABS:
            raise AssertionError(f"tool tabs are not sorted and complete: {coverage}")
        if coverage.get("callbackTools") != EXPECTED_CALLBACKS:
            raise AssertionError(f"callback tool list mismatch: {coverage}")
        if coverage.get("callbackToolCount") != len(EXPECTED_CALLBACKS) or coverage.get("callbackToolParity") is not True:
            raise AssertionError(f"callback tool count/parity mismatch: {coverage}")
        if coverage.get("alwaysVisibleTools") != EXPECTED_ALWAYS_VISIBLE:
            raise AssertionError(f"always-visible tool list mismatch: {coverage}")
        if coverage.get("alwaysVisibleToolCount") != len(EXPECTED_ALWAYS_VISIBLE) or coverage.get("alwaysVisibleToolParity") is not True:
            raise AssertionError(f"always-visible tool count/parity mismatch: {coverage}")

        tab_map = coverage.get("tabToolMap") or {}
        tab_counts = coverage.get("tabToolCounts") or {}
        if sorted(tab_map) != EXPECTED_TABS or sorted(tab_counts) != EXPECTED_TABS:
            raise AssertionError(f"tab tool map/count keys mismatch: {coverage}")
        for tab, names in tab_map.items():
            if tab_counts.get(tab) != len(names):
                raise AssertionError(f"tab tool count mismatch for {tab}: {coverage}")
            if names != sorted(names):
                raise AssertionError(f"tab tool map is not sorted for {tab}: {coverage}")
        if coverage.get("tabToolCountParity") is not True:
            raise AssertionError(f"tab tool count parity mismatch: {coverage}")

        execution_counts = coverage.get("executionCounts") or {}
        if execution_counts.get("callback") != len(EXPECTED_CALLBACKS):
            raise AssertionError(f"callback execution count mismatch: {coverage}")
        if execution_counts.get("subprocess") != coverage.get("toolCount") - len(EXPECTED_CALLBACKS):
            raise AssertionError(f"subprocess execution count mismatch: {coverage}")
        if coverage.get("executionCountParity") is not True:
            raise AssertionError(f"execution count parity mismatch: {coverage}")

        result_mode_counts = coverage.get("resultModeCounts") or {}
        structured_rows = [tool for tool in tools if tool.get("resultMode") == "structured"]
        raw_rows = [tool for tool in tools if tool.get("resultMode") == "raw"]
        if result_mode_counts.get("structured") != len(structured_rows):
            raise AssertionError(f"structured result-mode count mismatch: {coverage}")
        if result_mode_counts.get("raw") != len(raw_rows):
            raise AssertionError(f"raw result-mode count mismatch: {coverage}")
        if coverage.get("resultModeCountParity") is not True:
            raise AssertionError(f"result-mode count parity mismatch: {coverage}")

        index = request("GET", "/qa/coverage-index")
        group = (index.get("groups") or {}).get("toolsAndParsers") or {}
        for key in (
            "toolRegistryTabToolMap",
            "toolRegistryTabToolCounts",
            "toolRegistryCallbackTools",
            "toolRegistryAlwaysVisibleTools",
            "toolRegistryExecutionCounts",
            "toolRegistryResultModeCounts",
        ):
            if key not in group:
                raise AssertionError(f"coverage index missing tool registry detail {key}: {group}")
        if group.get("toolRegistryTabToolMap") != coverage.get("tabToolMap"):
            raise AssertionError(f"coverage index tab tool map mirror mismatch: {group}")
        if group.get("toolRegistryExecutionCounts") != coverage.get("executionCounts"):
            raise AssertionError(f"coverage index execution-count mirror mismatch: {group}")
        if group.get("toolRegistryResultModeCounts") != coverage.get("resultModeCounts"):
            raise AssertionError(f"coverage index result-mode mirror mismatch: {group}")

        print("tool-catalog-detail proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"tool-catalog-detail proof failed: {exc}", flush=True)
        raise SystemExit(1)
