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

REQUIRED_ENDPOINTS = {
    "/state",
    "/messages",
    "/results",
    "/qa/tool-coverage",
    "/qa/subtab-coverage",
    "/qa/agent-loop-coverage",
    "/qa/tool-flow-coverage",
    "/qa/runtime-coverage",
    "/qa/context-coverage",
    "/qa/settings-coverage",
    "/qa/visual-coverage",
    "/qa/session-coverage",
    "/qa/tab-action-coverage",
    "/qa/chat-coverage",
    "/qa/result-parser-coverage",
    "/qa/tool-family-fanout-coverage",
}

REQUIRED_PROOFS = {
    "app-qa-matrix-smoke-proof.py",
    "tool-registry-coverage-proof.py",
    "subtab-coverage-proof.py",
    "agent-loop-coverage-proof.py",
    "tool-flow-coverage-proof.py",
    "runtime-coverage-proof.py",
    "context-coverage-proof.py",
    "settings-coverage-proof.py",
    "visual-coverage-proof.py",
    "session-coverage-proof.py",
    "tab-action-coverage-proof.py",
    "chat-coverage-proof.py",
    "result-parser-routing-proof.py",
    "tool-family-fanout-coverage-proof.py",
}

REQUIRED_GROUPS = {
    "appState",
    "chatAndContext",
    "runtimeAndCache",
    "settingsAndVisuals",
    "toolsAndParsers",
    "tabsAndSessions",
}


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


def assert_coverage_index() -> None:
    state = request("GET", "/state")
    index = request("GET", "/qa/coverage-index")

    if index.get("ok") is not True:
        raise AssertionError(f"/qa/coverage-index failed: {index}")
    if index.get("endpointCount", 0) < len(REQUIRED_ENDPOINTS):
        raise AssertionError(f"coverage index endpoint count mismatch: {index}")
    if index.get("proofCount", 0) < len(REQUIRED_PROOFS):
        raise AssertionError(f"coverage index proof count mismatch: {index}")

    endpoints = set(index.get("endpoints") or [])
    missing_endpoints = sorted(REQUIRED_ENDPOINTS.difference(endpoints))
    if missing_endpoints:
        raise AssertionError(f"coverage index missing endpoints {missing_endpoints}: {index}")

    proofs = set(index.get("proofs") or [])
    missing_proofs = sorted(REQUIRED_PROOFS.difference(proofs))
    if missing_proofs:
        raise AssertionError(f"coverage index missing proofs {missing_proofs}: {index}")
    missing_files = sorted(name for name in REQUIRED_PROOFS if not (ROOT / "scripts" / name).is_file())
    if missing_files:
        raise AssertionError(f"coverage index names non-existent proof files: {missing_files}")

    groups = index.get("groups") or {}
    missing_groups = sorted(name for name in REQUIRED_GROUPS if name not in groups)
    if missing_groups:
        raise AssertionError(f"coverage index missing groups {missing_groups}: {index}")
    for name, group in groups.items():
        endpoints_for_group = group.get("endpoints") or []
        proofs_for_group = group.get("proofs") or []
        if not endpoints_for_group:
            raise AssertionError(f"coverage index group has no endpoints {name}: {group}")
        if not proofs_for_group:
            raise AssertionError(f"coverage index group has no proofs {name}: {group}")
        if group.get("endpointCount") != len(endpoints_for_group):
            raise AssertionError(f"coverage index group endpoint count mismatch {name}: {group}")
        if group.get("proofCount") != len(proofs_for_group):
            raise AssertionError(f"coverage index group proof count mismatch {name}: {group}")
    runtime_group = groups.get("runtimeAndCache") or {}
    if runtime_group.get("liveProofArtifactCount", 0) < 6:
        raise AssertionError(f"coverage index runtime live artifact count mismatch: {runtime_group}")
    if (groups.get("chatAndContext") or {}).get("stateKeyCount", 0) < 19:
        raise AssertionError(f"coverage index chat/context state key count mismatch: {groups.get('chatAndContext')}")
    if (groups.get("toolsAndParsers") or {}).get("stateKeyCount", 0) < 5:
        raise AssertionError(f"coverage index tools/parsers state key count mismatch: {groups.get('toolsAndParsers')}")
    if (groups.get("tabsAndSessions") or {}).get("stateKeyCount", 0) < 12:
        raise AssertionError(f"coverage index tabs/sessions state key count mismatch: {groups.get('tabsAndSessions')}")
    if (groups.get("tabsAndSessions") or {}).get("actionStateKeyCount", 0) < 26:
        raise AssertionError(f"coverage index tabs/sessions action state key count mismatch: {groups.get('tabsAndSessions')}")

    qa = state.get("qaCoverage") or {}
    if "/qa/coverage-index" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing coverage-index route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_coverage_index()
        print("coverage-index proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"coverage-index proof failed: {exc}", flush=True)
        raise SystemExit(1)
