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


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-stash-retrieval")
        if seeded.get("ok") is not True:
            raise AssertionError(f"stash retrieval seed failed: {seeded}")
        active_op = seeded["activeOpId"]

        packet = request("POST", "/qa/context-packet", {
            "query": "kerberos golden ticket lateral movement",
            "maxSnippets": 2,
            "includeAssets": False,
            "includeFindings": False,
            "includeRecentToolOutput": False,
            "includeStash": True,
            "cveMode": "off",
            "activeOpId": active_op,
        })["packet"]
        if "kerberos-golden-ticket-note" not in packet:
            raise AssertionError(f"targeted stash note missing from selected context:\n{packet}")
        if "inactive-kerberos-secret" in packet:
            raise AssertionError(f"inactive op stash leaked into selected context:\n{packet}")
        if "unrelated-noise-note" in packet:
            raise AssertionError(f"unrelated stash noise displaced targeted retrieval:\n{packet}")

        state = request("GET", "/state")
        retrieval = state.get("stashRetrieval") or {}
        if retrieval.get("query") != "kerberos golden ticket lateral movement":
            raise AssertionError(f"stash retrieval audit query missing: {retrieval}")
        if retrieval.get("candidateCount", 0) < 3 or retrieval.get("returnedCount", 0) < 1:
            raise AssertionError(f"stash retrieval audit counts missing: {retrieval}")
        labels = retrieval.get("topLabels") or []
        if labels[:1] != ["kerberos-golden-ticket-note"]:
            raise AssertionError(f"targeted stash note was not top-ranked: {retrieval}")
        if retrieval.get("topScore", 0) <= 0:
            raise AssertionError(f"stash retrieval did not expose positive score: {retrieval}")

        print("stash-retrieval proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"stash-retrieval proof failed: {exc}", flush=True)
        raise SystemExit(1)
