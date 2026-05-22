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


def stash_actions() -> dict:
    state = request("GET", "/state")
    actions = state.get("stashActions") or {}
    if "addSheetVisible" not in actions:
        raise AssertionError(f"stash add sheet visibility missing from state: {actions}")
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
        actions = stash_actions()
        if actions.get("addSheetVisible") is not False:
            raise AssertionError(f"stash add sheet should start hidden: {actions}")

        opened = request("POST", "/qa/stash-add-sheet", {"action": "open"})
        if opened.get("ok") is not True:
            raise AssertionError(f"stash add sheet open failed: {opened}")
        actions = stash_actions()
        if actions.get("lastAction") != "openAddSheet" or actions.get("addSheetVisible") is not True:
            raise AssertionError(f"stash add sheet open state mismatch: {actions}")

        cancelled = request("POST", "/qa/stash-add-sheet", {"action": "cancel"})
        if cancelled.get("ok") is not True:
            raise AssertionError(f"stash add sheet cancel failed: {cancelled}")
        actions = stash_actions()
        if actions.get("lastAction") != "cancelAddSheet" or actions.get("addSheetVisible") is not False:
            raise AssertionError(f"stash add sheet cancel state mismatch: {actions}")

        added = request("POST", "/qa/stash-add-sheet", {
            "action": "add",
            "label": "qa-stash-sheet-added",
            "content": "qa stash add sheet content for dynamic context catalogue",
        })
        item_id = added.get("itemId")
        if added.get("ok") is not True or not item_id:
            raise AssertionError(f"stash add sheet submit failed: {added}")
        actions = stash_actions()
        if actions.get("lastAction") != "add" or actions.get("addSheetVisible") is not False:
            raise AssertionError(f"stash add sheet submit state mismatch: {actions}")
        if actions.get("lastItemId") != item_id or actions.get("itemCount") != 2:
            raise AssertionError(f"stash add sheet item state mismatch: {actions}")

        print("stash-add-sheet proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"stash-add-sheet proof failed: {exc}", flush=True)
        raise SystemExit(1)
