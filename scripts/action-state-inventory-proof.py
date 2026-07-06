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
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
APP_STATE = ROOT / "ExploitBot" / "Sources" / "ExploitBot" / "Models" / "AppState.swift"

EXPECTED_GROUPS = [
    "chatAndControl",
    "navigationAndPhase",
    "agents",
    "settings",
    "tabTools",
    "reportingAndEvidence",
]

EXPECTED_PROOFS = [
    "action-state-inventory-proof.py",
    "app-qa-matrix-smoke-proof.py",
    "coverage-index-proof.py",
    "chat-actions-proof.py",
    "chat-control-actions-proof.py",
    "window-overlay-actions-proof.py",
    "tab-switch-action-proof.py",
    "phase-action-proof.py",
    "activity-feed-actions-proof.py",
    "agent-actions-proof.py",
    "agent-settings-actions-proof.py",
    "settings-engine-actions-proof.py",
    "tool-settings-actions-proof.py",
    "cve-settings-actions-proof.py",
    "inference-log-actions-proof.py",
    "recon-action-status-proof.py",
    "recon-copy-actions-proof.py",
    "web-verify-action-proof.py",
    "web-direct-actions-proof.py",
    "web-row-context-actions-proof.py",
    "network-protocol-action-proof.py",
    "network-copy-actions-proof.py",
    "creds-action-results-proof.py",
    "creds-copy-actions-proof.py",
    "exploit-action-differentiation-proof.py",
    "exploit-copy-actions-proof.py",
    "post-copy-actions-proof.py",
    "osint-artifact-actions-proof.py",
    "osint-copy-actions-proof.py",
    "report-generate-action-proof.py",
    "report-visible-export-actions-proof.py",
    "report-agent-action-proof.py",
    "report-finding-actions-proof.py",
    "stash-actions-proof.py",
    "stash-row-context-actions-proof.py",
]


def source_text() -> str:
    return APP_STATE.read_text(encoding="utf-8")


def source_action_states() -> list[str]:
    return re.findall(r"^struct\s+(\w*ActionState)\s*\{", source_text(), re.MULTILINE)


def source_state_vars() -> list[tuple[str, str, bool]]:
    text = source_text()
    direct = re.findall(r"^\s{4}var\s+(\w+)\s*=\s*(\w*ActionState)\(", text, re.MULTILINE)
    history = re.findall(r"^\s{4}var\s+(\w+):\s+\[(\w*ActionState)\]\s*=", text, re.MULTILINE)
    return [(name, typ, False) for name, typ in direct] + [(name, typ, True) for name, typ in history]


def source_snapshot_functions() -> list[str]:
    return re.findall(r"private static func (\w*ActionSnapshot)\(", source_text())


def source_record_functions() -> list[str]:
    names = re.findall(r"func\s+(record\w*Action)\s*\(", source_text())
    return list(dict.fromkeys(names))


def source_action_routes() -> list[str]:
    return [
        f"{method} {path}"
        for method, path in re.findall(r'case \("([A-Z]+)", "([^"]*action[^"]*)"\):', source_text(), re.IGNORECASE)
    ]


def request(method: str, path: str, body: str | None = None, timeout: float = 45.0):
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

        payload = request("GET", "/qa/action-state-inventory")
        states = source_action_states()
        state_vars = source_state_vars()
        snapshot_functions = source_snapshot_functions()
        record_functions = source_record_functions()
        action_routes = source_action_routes()

        if payload.get("ok") is not True:
            raise AssertionError(f"action-state inventory failed: {payload}")
        if payload.get("source") != "AppState.swift":
            raise AssertionError(f"action-state inventory source mismatch: {payload}")
        if payload.get("actionStateCount") != len(states):
            raise AssertionError(f"action-state inventory struct count mismatch: {payload}")
        if [item.get("type") for item in payload.get("actionStates") or []] != states:
            raise AssertionError(f"action-state inventory struct list mismatch: {payload}")
        if any(not item.get("stateField") for item in payload.get("actionStates") or []):
            raise AssertionError(f"action-state inventory has missing state fields: {payload}")
        if any(not item.get("snapshotFunction") for item in payload.get("actionStates") or []):
            raise AssertionError(f"action-state inventory has missing snapshot functions: {payload}")
        if any(not item.get("proofOwner") for item in payload.get("actionStates") or []):
            raise AssertionError(f"action-state inventory has missing proof owners: {payload}")
        if any(not item.get("group") for item in payload.get("actionStates") or []):
            raise AssertionError(f"action-state inventory has missing groups: {payload}")
        if payload.get("snapshotParity") is not True:
            raise AssertionError(f"action-state inventory snapshot parity mismatch: {payload}")
        if payload.get("stateFieldParity") is not True:
            raise AssertionError(f"action-state inventory state field parity mismatch: {payload}")

        if payload.get("stateVars") != [
            {"field": name, "type": typ, "isHistory": is_history} for name, typ, is_history in state_vars
        ]:
            raise AssertionError(f"action-state inventory state var list mismatch: {payload}")
        if payload.get("stateVarCount") != len(state_vars):
            raise AssertionError(f"action-state inventory state var count mismatch: {payload}")
        if payload.get("snapshotFunctions") != snapshot_functions:
            raise AssertionError(f"action-state inventory snapshot function list mismatch: {payload}")
        if payload.get("snapshotFunctionCount") != len(snapshot_functions):
            raise AssertionError(f"action-state inventory snapshot function count mismatch: {payload}")
        if payload.get("recordFunctions") != record_functions:
            raise AssertionError(f"action-state inventory record function list mismatch: {payload}")
        if payload.get("recordFunctionCount") != len(record_functions):
            raise AssertionError(f"action-state inventory record function count mismatch: {payload}")
        if payload.get("actionRoutes") != action_routes:
            raise AssertionError(f"action-state inventory action route list mismatch: {payload}")
        if payload.get("actionRouteCount") != len(action_routes):
            raise AssertionError(f"action-state inventory action route count mismatch: {payload}")

        if payload.get("groups") != EXPECTED_GROUPS:
            raise AssertionError(f"action-state inventory group list mismatch: {payload}")
        group_counts = payload.get("groupCounts") or {}
        if set(group_counts) != set(EXPECTED_GROUPS):
            raise AssertionError(f"action-state inventory group count keys mismatch: {payload}")
        if sum(group_counts.values()) != len(states):
            raise AssertionError(f"action-state inventory group counts do not cover structs: {payload}")

        state = request("GET", "/state")
        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/action-state-inventory" not in state_routes:
            raise AssertionError(f"state route list missing action-state inventory route: {state_routes}")

        index = request("GET", "/qa/coverage-index", timeout=120.0)
        app_group = (index.get("groups") or {}).get("appState") or {}
        if app_group.get("actionStateInventoryCount") != payload.get("actionStateCount"):
            raise AssertionError(f"coverage index action-state count mismatch: {index}")
        if app_group.get("actionStateInventoryGroups") != payload.get("groupCounts"):
            raise AssertionError(f"coverage index action-state group mismatch: {index}")
        if app_group.get("actionStateInventoryProofFileParity") != payload.get("proofFileParity"):
            raise AssertionError(f"coverage index action-state proof parity mismatch: {index}")

        proofs = payload.get("proofs") or []
        if proofs != EXPECTED_PROOFS:
            raise AssertionError(f"action-state inventory proof list mismatch: {payload}")
        if payload.get("proofCount") != len(EXPECTED_PROOFS):
            raise AssertionError(f"action-state inventory proof count mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"action-state inventory proof-file parity mismatch: {payload}")
        missing_files = sorted(name for name in EXPECTED_PROOFS if not (ROOT / "scripts" / name).is_file())
        if missing_files:
            raise AssertionError(f"action-state inventory names missing proof files: {missing_files}")

        print("action-state-inventory proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"action-state-inventory proof failed: {exc}", flush=True)
        raise SystemExit(1)
