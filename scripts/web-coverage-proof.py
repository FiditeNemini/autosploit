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

REQUIRED_SURFACES = [
    "vulnerabilityRows",
    "createFinding",
    "stashFinding",
    "copyFinding",
    "copyAll",
    "headerCopy",
    "rowContextActions",
    "relatedCveSearch",
    "verifyProgress",
    "contextHandoff",
    "activityTelemetry",
]

REQUIRED_ROUTES = [
    "/qa/seed-web-direct-actions",
    "/qa/web-create-finding",
    "/qa/web-stash",
    "/qa/web-copy",
    "/qa/web-copy-all",
    "/qa/web-row-action",
    "/qa/web-search-related",
    "/qa/seed-web-verify-action",
]

REQUIRED_STATE_KEYS = [
    "webAction",
    "webDirectActions",
    "stashActions",
    "findingWizard",
    "chat",
    "messages",
    "tabActivities",
    "feedRecent",
]

REQUIRED_PROOFS = [
    "web-direct-actions-proof.py",
    "web-header-copy-proof.py",
    "web-row-context-actions-proof.py",
    "web-verify-action-proof.py",
    "visual-web-verify-proof.py",
]


def request(method: str, path: str, body: str | None = None, timeout: float = 45.0):
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

        coverage = request("GET", "/qa/web-coverage")
        if coverage.get("ok") is not True:
            raise AssertionError(f"web coverage failed: {coverage}")
        if coverage.get("webSurfaces") != REQUIRED_SURFACES:
            raise AssertionError(f"web surface list mismatch: {coverage}")
        if coverage.get("webSurfaceCount") != len(REQUIRED_SURFACES):
            raise AssertionError(f"web surface count mismatch: {coverage}")
        if coverage.get("webSurfaceParity") is not True:
            raise AssertionError(f"web surface parity mismatch: {coverage}")
        if coverage.get("routes") != REQUIRED_ROUTES:
            raise AssertionError(f"web route list mismatch: {coverage}")
        if coverage.get("routeCount") != len(REQUIRED_ROUTES):
            raise AssertionError(f"web route count mismatch: {coverage}")
        if coverage.get("routeParity") is not True:
            raise AssertionError(f"web route parity mismatch: {coverage}")
        if coverage.get("stateKeys") != REQUIRED_STATE_KEYS:
            raise AssertionError(f"web state-key list mismatch: {coverage}")
        if coverage.get("stateKeyCount") != len(REQUIRED_STATE_KEYS):
            raise AssertionError(f"web state-key count mismatch: {coverage}")
        if coverage.get("stateKeyParity") is not True:
            raise AssertionError(f"web state-key parity mismatch: {coverage}")
        if coverage.get("proofs") != REQUIRED_PROOFS:
            raise AssertionError(f"web proof list mismatch: {coverage}")
        if coverage.get("proofCount") != len(REQUIRED_PROOFS):
            raise AssertionError(f"web proof count mismatch: {coverage}")
        if coverage.get("proofFileParity") is not True:
            raise AssertionError(f"web proof-file parity mismatch: {coverage}")
        for contract in (
            "vulnFindingHandoff",
            "stashHandoff",
            "relatedCveSearch",
            "verifyProgress",
            "rowContextActions",
            "activityTelemetry",
        ):
            if (coverage.get("contracts") or {}).get(contract) is not True:
                raise AssertionError(f"web contract {contract} missing: {coverage}")

        state = request("GET", "/state")
        qa = state.get("qaCoverage") or {}
        if "/qa/web-coverage" not in (qa.get("stateRoutes") or []):
            raise AssertionError(f"state route list missing web coverage: {qa}")

        index = request("GET", "/qa/coverage-index")
        group = (index.get("groups") or {}).get("tabsAndSessions") or {}
        if group.get("webSurfaces") != coverage.get("webSurfaces"):
            raise AssertionError(f"coverage-index web surface mirror mismatch: {index}")
        if group.get("webSurfaceParity") != coverage.get("webSurfaceParity"):
            raise AssertionError(f"coverage-index web surface parity mismatch: {index}")
        if group.get("webProofs") != coverage.get("proofs"):
            raise AssertionError(f"coverage-index web proof mirror mismatch: {index}")
        if group.get("webProofFileParity") != coverage.get("proofFileParity"):
            raise AssertionError(f"coverage-index web proof-file parity mismatch: {index}")
        if group.get("webStateKeys") != coverage.get("stateKeys"):
            raise AssertionError(f"coverage-index web state-key mirror mismatch: {index}")
        if group.get("webContracts") != coverage.get("contracts"):
            raise AssertionError(f"coverage-index web contract mirror mismatch: {index}")

        print("web-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"web-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
