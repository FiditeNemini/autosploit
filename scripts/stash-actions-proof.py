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


def stash_actions(state: dict) -> dict:
    actions = state.get("stashActions") or {}
    for label in ("Add", "Copy All", "Copy", "Send", "Delete"):
        if label not in actions.get("actionLabels", []):
            raise AssertionError(f"stash action label {label!r} missing: {actions}")
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

        seeded = request("POST", "/qa/seed-stash-actions")
        if seeded.get("ok") is not True:
            raise AssertionError(f"stash action seed failed: {seeded}")
        state = request("GET", "/state")
        actions = stash_actions(state)
        if actions.get("itemCount") != 1 or actions.get("lastAction") != "seeded":
            raise AssertionError(f"stash seed state mismatch: {actions}")

        added = request("POST", "/qa/stash-add", {
            "label": "qa-stash-action-added",
            "content": "qa stash action content for CVE-2021-41773",
            "type": "note",
        })
        item_id = added.get("itemId")
        if added.get("ok") is not True or not item_id:
            raise AssertionError(f"stash add failed: {added}")
        state = request("GET", "/state")
        actions = stash_actions(state)
        if actions.get("lastAction") != "add" or actions.get("itemCount") != 2:
            raise AssertionError(f"stash add state mismatch: {actions}")

        copied_all = request("POST", "/qa/stash-copy-all")
        if copied_all.get("ok") is not True:
            raise AssertionError(f"stash copy all failed: {copied_all}")
        state = request("GET", "/state")
        actions = stash_actions(state)
        if actions.get("lastAction") != "copyAll" or actions.get("clipboardPreview", "").find("qa-stash-action-added") == -1:
            raise AssertionError(f"stash copy-all state mismatch: {actions}")

        copied_item = request("POST", "/qa/stash-copy", item_id)
        if copied_item.get("ok") is not True:
            raise AssertionError(f"stash copy item failed: {copied_item}")
        state = request("GET", "/state")
        actions = stash_actions(state)
        if actions.get("lastAction") != "copy" or actions.get("lastItemId") != item_id:
            raise AssertionError(f"stash copy item state mismatch: {actions}")

        sent = request("POST", "/qa/stash-send", item_id)
        if sent.get("ok") is not True:
            raise AssertionError(f"stash send failed: {sent}")
        messages = request("GET", "/messages")
        if not any(m.get("role") == "user" and "qa stash action content" in m.get("content", "") for m in messages):
            raise AssertionError(f"stash send did not append bounded user message: {messages}")
        state = request("GET", "/state")
        actions = stash_actions(state)
        if actions.get("lastAction") != "send" or actions.get("lastItemId") != item_id:
            raise AssertionError(f"stash send state mismatch: {actions}")

        deleted = request("POST", "/qa/stash-delete", item_id)
        if deleted.get("ok") is not True:
            raise AssertionError(f"stash delete failed: {deleted}")
        state = request("GET", "/state")
        actions = stash_actions(state)
        if actions.get("lastAction") != "delete" or actions.get("lastDeletedId") != item_id or actions.get("itemCount") != 1:
            raise AssertionError(f"stash delete state mismatch: {actions}")
        activity = state.get("tabActivities", {}).get("stash", {})
        if activity.get("status") != "done" or activity.get("lastTool") != "delete_stash":
            raise AssertionError(f"stash tab activity did not show delete completion: {activity}")

        print("stash-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"stash-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
