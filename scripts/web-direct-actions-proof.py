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


def web_actions(state: dict) -> dict:
    actions = state.get("webDirectActions") or {}
    for label in ("Create Finding", "Stash", "Copy", "Search Related CVEs"):
        if label not in actions.get("actionLabels", []):
            raise AssertionError(f"web action label {label!r} missing: {actions}")
    return actions


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-web-direct-actions")
        if seeded.get("ok") is not True:
            raise AssertionError(f"web direct action seed failed: {seeded}")
        state = request("GET", "/state")
        actions = web_actions(state)
        if state.get("activeTab") != "web" or actions.get("lastAction") != "seeded":
            raise AssertionError(f"web action seed state mismatch: {state}")

        created = request("POST", "/qa/web-create-finding")
        if created.get("ok") is not True:
            raise AssertionError(f"web create finding failed: {created}")
        state = request("GET", "/state")
        actions = web_actions(state)
        prefill = actions.get("findingPrefill") or {}
        if actions.get("lastAction") != "createFinding" or actions.get("findingWizardVisible") is not True:
            raise AssertionError(f"web create finding state mismatch: {actions}")
        if prefill.get("title") != "Apache 2.4.49 Path Traversal" or prefill.get("cve") != "CVE-2021-41773":
            raise AssertionError(f"web finding prefill missing seeded vuln: {actions}")

        stashed = request("POST", "/qa/web-stash")
        if stashed.get("ok") is not True:
            raise AssertionError(f"web stash failed: {stashed}")
        state = request("GET", "/state")
        actions = web_actions(state)
        if actions.get("lastAction") != "stash" or actions.get("stashCount") != 1:
            raise AssertionError(f"web stash state mismatch: {actions}")
        if "Apache 2.4.49 Path Traversal" not in actions.get("lastStashPreview", ""):
            raise AssertionError(f"web stash preview missing vuln evidence: {actions}")

        copied = request("POST", "/qa/web-copy")
        if copied.get("ok") is not True:
            raise AssertionError(f"web copy failed: {copied}")
        state = request("GET", "/state")
        actions = web_actions(state)
        if actions.get("lastAction") != "copy" or "Apache 2.4.49 Path Traversal" not in actions.get("clipboardPreview", ""):
            raise AssertionError(f"web copy state mismatch: {actions}")

        searched = request("POST", "/qa/web-search-related")
        if searched.get("ok") is not True:
            raise AssertionError(f"web search related failed: {searched}")
        state = request("GET", "/state")
        actions = web_actions(state)
        if actions.get("lastAction") != "searchRelated":
            raise AssertionError(f"web search related state mismatch: {actions}")
        if "search_cve apache http_server" not in actions.get("lastPrompt", ""):
            raise AssertionError(f"web search related prompt missing cve product: {actions}")
        messages = request("GET", "/messages")
        if not any("search_cve apache http_server" in m.get("content", "") for m in messages):
            raise AssertionError(f"web search related did not send prompt to chat: {messages}")
        activity = state.get("tabActivities", {}).get("web", {})
        if activity.get("status") != "running" or activity.get("lastTool") != "search_related_cve":
            raise AssertionError(f"web tab activity did not expose related-CVE search: {activity}")

        print("web-direct-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"web-direct-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
