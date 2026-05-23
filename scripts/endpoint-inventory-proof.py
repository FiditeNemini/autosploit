#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
APP_STATE = ROOT / "ExploitBot" / "Sources" / "ExploitBot" / "Models" / "AppState.swift"

EXPECTED_GROUPS = [
    "appState",
    "chatAndControl",
    "engineAndRuntime",
    "agents",
    "settings",
    "contextAndEvidence",
    "toolsAndParsers",
    "tabsAndActions",
    "ledgersAndRelease",
    "opsAndPersistence",
]

EXPECTED_PROOFS = [
    "endpoint-inventory-proof.py",
    "app-qa-matrix-smoke-proof.py",
    "coverage-index-proof.py",
    "chat-turn-controls-proof.py",
    "runtime-coverage-proof.py",
    "agent-loop-coverage-proof.py",
    "settings-coverage-proof.py",
    "context-coverage-proof.py",
    "tool-flow-coverage-proof.py",
    "tab-action-coverage-proof.py",
    "audit-ledger-proof.py",
    "persistence-proof.py",
]


def source_routes() -> list[tuple[str, str]]:
    text = APP_STATE.read_text(encoding="utf-8")
    return re.findall(r'case \("([A-Z]+)", "([^"]+)"\):', text)


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

        routes = source_routes()
        payload = request("GET", "/qa/endpoint-inventory")
        if payload.get("ok") is not True:
            raise AssertionError(f"endpoint inventory route failed: {payload}")
        if payload.get("source") != "AppState.swift":
            raise AssertionError(f"endpoint inventory source mismatch: {payload}")
        if payload.get("routeCount") != len(routes):
            raise AssertionError(f"endpoint inventory route count mismatch: {payload}")
        if payload.get("routeParity") is not True:
            raise AssertionError(f"endpoint inventory route parity mismatch: {payload}")

        expected_method_counts = dict(sorted(Counter(method for method, _ in routes).items()))
        if payload.get("methodCounts") != expected_method_counts:
            raise AssertionError(f"endpoint inventory method counts mismatch: {payload}")

        listed_routes = [(item.get("method"), item.get("path")) for item in payload.get("routes") or []]
        if listed_routes != routes:
            raise AssertionError(f"endpoint inventory route list mismatch: {payload}")
        if any(not item.get("group") for item in payload.get("routes") or []):
            raise AssertionError(f"endpoint inventory has ungrouped routes: {payload}")
        if any(not item.get("proofOwner") for item in payload.get("routes") or []):
            raise AssertionError(f"endpoint inventory has routes without proof owner: {payload}")

        if payload.get("groups") != EXPECTED_GROUPS:
            raise AssertionError(f"endpoint inventory group list mismatch: {payload}")
        if payload.get("groupCount") != len(EXPECTED_GROUPS):
            raise AssertionError(f"endpoint inventory group count mismatch: {payload}")
        group_counts = payload.get("groupCounts") or {}
        if sum(group_counts.values()) != len(routes):
            raise AssertionError(f"endpoint inventory group counts do not cover routes: {payload}")
        if set(group_counts) != set(EXPECTED_GROUPS):
            raise AssertionError(f"endpoint inventory group count keys mismatch: {payload}")

        state = request("GET", "/state")
        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if payload.get("stateRoutes") != state_routes:
            raise AssertionError(f"endpoint inventory state route mirror mismatch: {payload}")
        if payload.get("stateRouteCount") != len(state_routes):
            raise AssertionError(f"endpoint inventory state route count mismatch: {payload}")
        if "/qa/endpoint-inventory" not in state_routes:
            raise AssertionError(f"state route list missing endpoint inventory route: {state_routes}")

        index = request("GET", "/qa/coverage-index")
        app_group = (index.get("groups") or {}).get("appState") or {}
        if app_group.get("endpointInventoryRouteCount") != payload.get("routeCount"):
            raise AssertionError(f"coverage index endpoint inventory count mismatch: {index}")
        if app_group.get("endpointInventoryGroupCounts") != payload.get("groupCounts"):
            raise AssertionError(f"coverage index endpoint inventory group mismatch: {index}")

        proofs = payload.get("proofs") or []
        if proofs != EXPECTED_PROOFS:
            raise AssertionError(f"endpoint inventory proof list mismatch: {payload}")
        if payload.get("proofCount") != len(EXPECTED_PROOFS):
            raise AssertionError(f"endpoint inventory proof count mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"endpoint inventory proof-file parity mismatch: {payload}")
        missing_files = sorted(name for name in EXPECTED_PROOFS if not (ROOT / "scripts" / name).is_file())
        if missing_files:
            raise AssertionError(f"endpoint inventory names missing proof files: {missing_files}")

        print("endpoint-inventory proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"endpoint-inventory proof failed: {exc}", flush=True)
        raise SystemExit(1)
