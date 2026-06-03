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
MAX_PACKET_CHARS = 6000
MAX_SELECTED_SNIPPETS = 8


def request(method: str, path: str, body: str | dict | None = None, timeout: float = 45.0):
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


def selected_snippet_count(packet: str) -> int:
    return sum(1 for line in packet.splitlines() if line.startswith("- ["))


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        for idx in range(20):
            request("POST", "/qa/stash-add", {
                "label": f"budget-marker-note-{idx:02d}",
                "type": "note",
                "content": (
                    f"budget marker snippet {idx:02d} "
                    + "repeatable context pressure "
                    + ("long-body-token " * 120)
                ),
            })

        packet = request("POST", "/qa/context-packet", {
            "query": "budget marker context pressure",
            "maxSnippets": 20,
            "includeAssets": False,
            "includeFindings": False,
            "includeRecentToolOutput": False,
            "includeStash": True,
            "cveMode": "off",
        })["packet"]

        if len(packet) > MAX_PACKET_CHARS:
            raise AssertionError(
                f"context packet exceeded prompt budget: {len(packet)} > {MAX_PACKET_CHARS}\n{packet}"
            )
        snippet_count = selected_snippet_count(packet)
        if snippet_count > MAX_SELECTED_SNIPPETS:
            raise AssertionError(
                f"context packet selected too many snippets: {snippet_count} > {MAX_SELECTED_SNIPPETS}\n{packet}"
            )
        if "Budget: max 6000 chars, max 8 selected snippets." not in packet:
            raise AssertionError(f"context packet missing explicit budget marker:\n{packet}")
        if "Use search_context for more targeted notes" not in packet:
            raise AssertionError(f"context packet missing on-demand context guidance:\n{packet}")

        print("context-packet-budget proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"context-packet-budget proof failed: {exc}", flush=True)
        raise SystemExit(1)
