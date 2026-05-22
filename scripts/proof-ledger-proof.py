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

SPECIAL_PROOFS = {
    "live-turn-harness.py",
    "verify-live-models.py",
    "prove-parser-api.py",
    "prove-block-l2-cache.py",
    "prove-ssm-rederive-status.py",
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


def expected_proofs() -> list[str]:
    names = []
    for path in (ROOT / "scripts").glob("*.py"):
        if path.name.endswith("-proof.py") or path.name in SPECIAL_PROOFS:
            names.append(path.name)
    return sorted(names)


def assert_proof_ledger() -> None:
    state = request("GET", "/state")
    ledger = request("GET", "/qa/proof-ledger")
    expected = expected_proofs()

    if ledger.get("ok") is not True:
        raise AssertionError(f"/qa/proof-ledger failed: {ledger}")
    if ledger.get("proofCount") != len(expected):
        raise AssertionError(f"proof ledger count mismatch expected {len(expected)}: {ledger}")
    proofs = ledger.get("proofs") or []
    if proofs != expected:
        missing = sorted(set(expected).difference(proofs))
        extra = sorted(set(proofs).difference(expected))
        raise AssertionError(f"proof ledger mismatch missing={missing} extra={extra}")
    categories = ledger.get("categories") or {}
    for key in ("agent", "chat", "runtime", "visual", "settings", "tools", "tabs", "context"):
        if (categories.get(key) or {}).get("count", 0) <= 0:
            raise AssertionError(f"proof ledger missing category {key}: {ledger}")
    if (categories.get("visual") or {}).get("count", 0) < 20:
        raise AssertionError(f"proof ledger visual category too small: {ledger}")
    if (categories.get("runtime") or {}).get("count", 0) < 8:
        raise AssertionError(f"proof ledger runtime category too small: {ledger}")

    qa = state.get("qaCoverage") or {}
    if "/qa/proof-ledger" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing proof-ledger route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_proof_ledger()
        print("proof-ledger proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"proof-ledger proof failed: {exc}", flush=True)
        raise SystemExit(1)
