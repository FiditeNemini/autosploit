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
REQUIRED_SECTIONS = ("## Goal", "## Changes", "## Proof")


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


def expected_checkpoints() -> list[Path]:
    return sorted((ROOT / "docs" / "checkpoints").glob("*.md"), key=checkpoint_number)


def checkpoint_number(path: Path) -> int:
    match = re.search(r"checkpoint-(\d+)\.md$", path.name)
    if not match:
        raise AssertionError(f"checkpoint doc missing numeric suffix: {path.relative_to(ROOT)}")
    return int(match.group(1))


def checkpoint_has_required_sections(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return all(section in text for section in REQUIRED_SECTIONS)


def assert_checkpoint_ledger() -> None:
    state = request("GET", "/state")
    ledger = request("GET", "/qa/checkpoint-ledger")
    checkpoints = expected_checkpoints()
    expected_paths = [str(path.relative_to(ROOT)) for path in checkpoints]
    expected_latest = str(max(checkpoints, key=checkpoint_number).relative_to(ROOT))
    expected_complete = [
        str(path.relative_to(ROOT))
        for path in checkpoints
        if checkpoint_has_required_sections(path)
    ]
    expected_complete_set = set(expected_complete)
    expected_incomplete = [path for path in expected_paths if path not in expected_complete_set]

    if ledger.get("ok") is not True:
        raise AssertionError(f"/qa/checkpoint-ledger failed: {ledger}")
    if ledger.get("checkpointCount") != len(checkpoints):
        raise AssertionError(f"checkpoint ledger count mismatch expected {len(checkpoints)}: {ledger}")
    if ledger.get("checkpoints") != expected_paths:
        raise AssertionError(f"checkpoint ledger path list mismatch: {ledger}")
    if ledger.get("completeCheckpointCount") != len(expected_complete):
        raise AssertionError(f"checkpoint ledger complete count mismatch: {ledger}")
    if ledger.get("completeCheckpoints") != expected_complete:
        raise AssertionError(f"checkpoint ledger complete list mismatch expected {expected_complete}: {ledger}")
    if ledger.get("incompleteCheckpoints") != expected_incomplete:
        raise AssertionError(f"checkpoint ledger incomplete list mismatch expected {expected_incomplete}: {ledger}")
    if ledger.get("latestCheckpoint") != expected_latest:
        raise AssertionError(f"checkpoint ledger latest checkpoint mismatch expected {expected_latest}: {ledger}")
    if ledger.get("latestCheckpointNumber") != checkpoint_number(max(checkpoints, key=checkpoint_number)):
        raise AssertionError(f"checkpoint ledger latest number mismatch: {ledger}")

    qa = state.get("qaCoverage") or {}
    if "/qa/checkpoint-ledger" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing checkpoint-ledger route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_checkpoint_ledger()
        print("checkpoint-ledger proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"checkpoint-ledger proof failed: {exc}", flush=True)
        raise SystemExit(1)
