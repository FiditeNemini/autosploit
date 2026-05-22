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


REMOVED_PROFILE_PATTERNS = (
    r"\bModelProfile\b",
    r"\bmodelProfile\b",
    r"\bmaxToolCount\b",
    r"\bmodelProfileHint\b",
    r"\bcuratedModels\b",
)

REQUIRED_CONTEXT_HOOKS = (
    "onContextUpdate",
    "search_context",
    "lastContextSummary",
    "lastToolSchemaNames",
    "context.catalog.maxSnippets",
)


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


def source_files() -> list[Path]:
    return sorted((ROOT / "ExploitBot" / "Sources" / "ExploitBot").rglob("*.swift"))


def assert_removed_profile_code() -> None:
    offenders: list[str] = []
    for path in source_files():
        text = path.read_text(encoding="utf-8")
        for pattern in REMOVED_PROFILE_PATTERNS:
            if re.search(pattern, text):
                offenders.append(f"{path.relative_to(ROOT)}:{pattern}")
    if offenders:
        raise AssertionError(f"removed model-profile code still present: {offenders}")


def assert_required_context_hooks() -> None:
    corpus = "\n".join(path.read_text(encoding="utf-8") for path in source_files())
    missing = [hook for hook in REQUIRED_CONTEXT_HOOKS if hook not in corpus]
    if missing:
        raise AssertionError(f"required context hooks missing: {missing}")


def assert_testserver_smoke() -> None:
    state = request("GET", "/state")
    messages = request("GET", "/messages")
    results = request("GET", "/results")

    required_state_keys = {
        "activeTab",
        "mode",
        "engineConfig",
        "contextCatalog",
        "requestContext",
        "agents",
        "toolSettings",
        "feedRecent",
    }
    missing = sorted(required_state_keys.difference(state))
    if missing:
        raise AssertionError(f"/state missing QA keys {missing}: {state}")
    if not isinstance(messages, list):
        raise AssertionError(f"/messages did not return a list: {messages}")
    for key in ("ports", "vulns", "osint", "postAttribution"):
        if key not in results or not isinstance(results[key], list):
            raise AssertionError(f"/results missing list key {key}: {results}")

    qa = state.get("qaCoverage") or {}
    if qa.get("staticProfilesRemoved") is not True:
        raise AssertionError(f"/state missing profile-removal QA coverage: {qa}")
    if qa.get("testServerSmoke") is not True:
        raise AssertionError(f"/state missing TestServer smoke QA coverage: {qa}")
    if sorted(qa.get("contextHooks") or []) != sorted(REQUIRED_CONTEXT_HOOKS):
        raise AssertionError(f"/state missing required context hook names: {qa}")


def run() -> None:
    assert_removed_profile_code()
    assert_required_context_hooks()

    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_testserver_smoke()
        print("app-qa-matrix-smoke proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"app-qa-matrix-smoke proof failed: {exc}", flush=True)
        raise SystemExit(1)
