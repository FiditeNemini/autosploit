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

EXPECTED_ROUTES = {
    "/qa/tool-coverage",
    "/qa/seed-result-parser-fixture",
    "/qa/result-parser-coverage",
    "/qa/seed-tool-family-fanout-fixture",
    "/qa/tool-family-fanout-coverage",
}
EXPECTED_PROOFS = {
    "tool-registry-coverage-proof.py",
    "result-parser-routing-proof.py",
    "result-context-catalog-proof.py",
    "tool-fanout-status-proof.py",
    "tool-family-fanout-coverage-proof.py",
}
EXPECTED_FAMILIES = {"recon", "web", "network", "creds", "exploit", "post", "osint"}
EXPECTED_STATE_KEYS = {
    "messages.toolCards",
    "tabActivities",
    "feedRecent",
    "contextCatalog",
    "results",
}


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

        coverage = request("GET", "/qa/tool-flow-coverage")
        if coverage.get("ok") is not True:
            raise AssertionError(f"tool flow coverage route failed: {coverage}")
        if set(coverage.get("routes") or []) != EXPECTED_ROUTES:
            raise AssertionError(f"tool flow route contract mismatch: {coverage}")
        if not EXPECTED_PROOFS.issubset(set(coverage.get("proofs") or [])):
            raise AssertionError(f"tool flow proofs missing: {coverage}")
        if coverage.get("proofCount", 0) < len(EXPECTED_PROOFS):
            raise AssertionError(f"tool flow proof count mismatch: {coverage}")
        missing_files = sorted(name for name in EXPECTED_PROOFS if not (ROOT / "scripts" / name).is_file())
        if missing_files:
            raise AssertionError(f"tool flow names non-existent proof files: {missing_files}")
        if set(coverage.get("families") or []) != EXPECTED_FAMILIES:
            raise AssertionError(f"tool flow family coverage mismatch: {coverage}")
        if coverage.get("toolCount") != 38:
            raise AssertionError(f"tool flow did not expose registry count: {coverage}")
        if coverage.get("callbackCount") != 3:
            raise AssertionError(f"tool flow did not expose callback count: {coverage}")
        expected_activity_statuses = ["running", "done", "failed", "canceled"]
        if coverage.get("tabActivityStatuses") != expected_activity_statuses:
            raise AssertionError(f"tool flow tab activity statuses mismatch: {coverage}")
        if coverage.get("tabActivityStatusCount") != len(expected_activity_statuses):
            raise AssertionError(f"tool flow tab activity status count mismatch: {coverage}")
        if coverage.get("tabActivityIndicatorContract") != "status-dot-running-ring":
            raise AssertionError(f"tool flow tab activity indicator contract mismatch: {coverage}")
        state_keys = set(coverage.get("stateKeys") or [])
        missing_state_keys = sorted(EXPECTED_STATE_KEYS.difference(state_keys))
        if missing_state_keys:
            raise AssertionError(f"tool flow missing state keys {missing_state_keys}: {coverage}")
        for key in ("registry", "parserRouting", "fanout", "contextCatalog"):
            if coverage.get("contracts", {}).get(key) is not True:
                raise AssertionError(f"tool flow contract missing {key}: {coverage}")

        registry = request("GET", "/qa/tool-coverage")
        if registry.get("ok") is not True:
            raise AssertionError(f"tool registry did not expose ok=true: {registry}")
        if registry.get("toolCount") != coverage.get("toolCount"):
            raise AssertionError(f"tool flow registry count disagrees with tool coverage: {coverage} {registry}")

        print("tool-flow-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"tool-flow-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
