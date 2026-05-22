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

REQUIRED_SUBTAB_PROOFS = (
    "recon-subtab-state-proof.py",
    "web-subtab-state-proof.py",
    "network-subtab-state-proof.py",
    "creds-subtab-state-proof.py",
    "exploit-subtab-state-proof.py",
    "post-subtab-state-proof.py",
    "osint-subtab-state-proof.py",
    "report-subtab-state-proof.py",
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
    subtab_coverage = request("GET", "/qa/subtab-coverage")
    agent_loop_coverage = request("GET", "/qa/agent-loop-coverage")
    tool_flow_coverage = request("GET", "/qa/tool-flow-coverage")
    runtime_coverage = request("GET", "/qa/runtime-coverage")
    context_coverage = request("GET", "/qa/context-coverage")
    settings_coverage = request("GET", "/qa/settings-coverage")

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
    if sorted(qa.get("subtabStateProofs") or []) != sorted(REQUIRED_SUBTAB_PROOFS):
        raise AssertionError(f"/state missing shared subtab-state proof coverage: {qa}")
    expected_subtab_tabs = ["creds", "exploit", "network", "osint", "post", "recon", "report", "web"]
    if sorted(qa.get("subtabStateTabs") or []) != expected_subtab_tabs:
        raise AssertionError(f"/state missing shared subtab-state tabs: {qa}")
    if "/qa/subtab-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing subtab coverage route contract: {qa}")
    if "/qa/agent-loop-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing agent loop coverage route contract: {qa}")
    if "/qa/tool-flow-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing tool flow coverage route contract: {qa}")
    if "/qa/runtime-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing runtime coverage route contract: {qa}")
    if "/qa/context-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing context coverage route contract: {qa}")
    if "/qa/settings-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing settings coverage route contract: {qa}")
    if subtab_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/subtab-coverage failed: {subtab_coverage}")
    if sorted((subtab_coverage.get("tabs") or {}).keys()) != expected_subtab_tabs:
        raise AssertionError(f"/qa/subtab-coverage tabs mismatch: {subtab_coverage}")
    if agent_loop_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/agent-loop-coverage failed: {agent_loop_coverage}")
    if agent_loop_coverage.get("modes") != {"autopilot": "execute", "copilot": "approval", "manual": "suggest"}:
        raise AssertionError(f"/qa/agent-loop-coverage mode contract mismatch: {agent_loop_coverage}")
    if tool_flow_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/tool-flow-coverage failed: {tool_flow_coverage}")
    if tool_flow_coverage.get("toolCount") != 38 or tool_flow_coverage.get("callbackCount") != 3:
        raise AssertionError(f"/qa/tool-flow-coverage registry counters mismatch: {tool_flow_coverage}")
    if runtime_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/runtime-coverage failed: {runtime_coverage}")
    if runtime_coverage.get("cacheResponseMethod") != "prefix-cache-l2-turboquant":
        raise AssertionError(f"/qa/runtime-coverage cache method mismatch: {runtime_coverage}")
    if context_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/context-coverage failed: {context_coverage}")
    if context_coverage.get("searchToolName") != "search_context":
        raise AssertionError(f"/qa/context-coverage search tool mismatch: {context_coverage}")
    if context_coverage.get("automaticInjectedContextCap") != 4:
        raise AssertionError(f"/qa/context-coverage context cap mismatch: {context_coverage}")
    if not 1 <= context_coverage.get("currentInjectedContextLimit", 0) <= 4:
        raise AssertionError(f"/qa/context-coverage current context limit mismatch: {context_coverage}")
    if settings_coverage.get("ok") is not True:
        raise AssertionError(f"/qa/settings-coverage failed: {settings_coverage}")
    if settings_coverage.get("categoryCount") != 9:
        raise AssertionError(f"/qa/settings-coverage category count mismatch: {settings_coverage}")
    if settings_coverage.get("cacheResponseMethod") != "prefix-cache-l2-turboquant":
        raise AssertionError(f"/qa/settings-coverage cache method mismatch: {settings_coverage}")


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
