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
SYSTEM_REVIEW = ROOT / "docs" / "app-system-review-2026-05-21.md"


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


def documented_current_gaps() -> list[str]:
    text = SYSTEM_REVIEW.read_text(encoding="utf-8")
    match = re.search(r"## Current Gaps To Close Next\n\n(?P<body>.*)$", text, flags=re.S)
    if not match:
        raise AssertionError("system review is missing Current Gaps To Close Next")
    body = match.group("body")
    gaps = []
    current: list[str] = []
    for line in body.splitlines():
        if re.match(r"^\d+\. ", line):
            if current:
                gaps.append(" ".join(current))
            current = [re.sub(r"^\d+\. ", "", line).strip()]
        elif current and (line.startswith("   ") or not line.strip()):
            if line.strip():
                current.append(line.strip())
    if current:
        gaps.append(" ".join(current))
    return gaps


def assert_gap_ledger() -> None:
    state = request("GET", "/state")
    ledger = request("GET", "/qa/gap-ledger")
    expected_gaps = documented_current_gaps()

    if ledger.get("ok") is not True:
        raise AssertionError(f"/qa/gap-ledger failed: {ledger}")
    if ledger.get("source") != "docs/app-system-review-2026-05-21.md#current-gaps-to-close-next":
        raise AssertionError(f"gap ledger source mismatch: {ledger}")
    if ledger.get("currentGapCount") != len(expected_gaps):
        raise AssertionError(f"gap ledger count mismatch expected {len(expected_gaps)}: {ledger}")
    if ledger.get("currentGaps") != expected_gaps:
        raise AssertionError(f"gap ledger current gaps mismatch expected {expected_gaps}: {ledger}")
    if ledger.get("unsupportedMultimodalBlocked") is not True:
        raise AssertionError(f"gap ledger should record Qwen VL is blocked: {ledger}")
    if set(ledger.get("supportedFamilies") or []) != {"qwen", "minimax"}:
        raise AssertionError(f"gap ledger supported families mismatch: {ledger}")
    if ledger.get("nextGap") != expected_gaps[0]:
        raise AssertionError(f"gap ledger next gap mismatch: {ledger}")

    qa = state.get("qaCoverage") or {}
    if "/qa/gap-ledger" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing gap-ledger route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_gap_ledger()
        print("gap-ledger proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"gap-ledger proof failed: {exc}", flush=True)
        raise SystemExit(1)
