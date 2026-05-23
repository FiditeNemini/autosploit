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
    "privescLifecycle",
    "adLifecycle",
    "lateralLifecycle",
    "attributionRows",
    "copyPrivesc",
    "copyAD",
    "copyLateral",
    "copyAttribution",
    "rawPostOutput",
    "activityTelemetry",
]

REQUIRED_ROUTES = [
    "/qa/seed-post-attribution",
    "/qa/seed-post-copy-actions",
    "/qa/post-copy",
]

REQUIRED_STATE_KEYS = [
    "postLifecycle",
    "postAttribution",
    "postCopyActions",
    "results.postAttribution",
    "results.rawResults",
    "tabActivities",
    "feedRecent",
]

REQUIRED_PROOFS = [
    "post-attribution-proof.py",
    "post-copy-actions-proof.py",
    "visual-post-attribution-proof.py",
]


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


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        coverage = request("GET", "/qa/post-coverage")
        if coverage.get("ok") is not True:
            raise AssertionError(f"post coverage failed: {coverage}")
        if coverage.get("postSurfaces") != REQUIRED_SURFACES:
            raise AssertionError(f"post surface list mismatch: {coverage}")
        if coverage.get("postSurfaceCount") != len(REQUIRED_SURFACES):
            raise AssertionError(f"post surface count mismatch: {coverage}")
        if coverage.get("postSurfaceParity") is not True:
            raise AssertionError(f"post surface parity mismatch: {coverage}")
        if coverage.get("routes") != REQUIRED_ROUTES:
            raise AssertionError(f"post route list mismatch: {coverage}")
        if coverage.get("routeCount") != len(REQUIRED_ROUTES):
            raise AssertionError(f"post route count mismatch: {coverage}")
        if coverage.get("routeParity") is not True:
            raise AssertionError(f"post route parity mismatch: {coverage}")
        if coverage.get("stateKeys") != REQUIRED_STATE_KEYS:
            raise AssertionError(f"post state-key list mismatch: {coverage}")
        if coverage.get("stateKeyCount") != len(REQUIRED_STATE_KEYS):
            raise AssertionError(f"post state-key count mismatch: {coverage}")
        if coverage.get("stateKeyParity") is not True:
            raise AssertionError(f"post state-key parity mismatch: {coverage}")
        if coverage.get("proofs") != REQUIRED_PROOFS:
            raise AssertionError(f"post proof list mismatch: {coverage}")
        if coverage.get("proofCount") != len(REQUIRED_PROOFS):
            raise AssertionError(f"post proof count mismatch: {coverage}")
        if coverage.get("proofFileParity") is not True:
            raise AssertionError(f"post proof-file parity mismatch: {coverage}")
        for contract in (
            "postAttribution",
            "copyActions",
            "lifecycleTelemetry",
            "rawPostOutput",
            "activityTelemetry",
        ):
            if (coverage.get("contracts") or {}).get(contract) is not True:
                raise AssertionError(f"post contract {contract} missing: {coverage}")

        state = request("GET", "/state")
        qa = state.get("qaCoverage") or {}
        if "/qa/post-coverage" not in (qa.get("stateRoutes") or []):
            raise AssertionError(f"state route list missing post coverage: {qa}")

        index = request("GET", "/qa/coverage-index")
        group = (index.get("groups") or {}).get("tabsAndSessions") or {}
        if group.get("postSurfaces") != coverage.get("postSurfaces"):
            raise AssertionError(f"coverage-index post surface mirror mismatch: {index}")
        if group.get("postSurfaceParity") != coverage.get("postSurfaceParity"):
            raise AssertionError(f"coverage-index post surface parity mismatch: {index}")
        if group.get("postProofs") != coverage.get("proofs"):
            raise AssertionError(f"coverage-index post proof mirror mismatch: {index}")
        if group.get("postProofFileParity") != coverage.get("proofFileParity"):
            raise AssertionError(f"coverage-index post proof-file parity mismatch: {index}")
        if group.get("postStateKeys") != coverage.get("stateKeys"):
            raise AssertionError(f"coverage-index post state-key mirror mismatch: {index}")
        if group.get("postContracts") != coverage.get("contracts"):
            raise AssertionError(f"coverage-index post contract mirror mismatch: {index}")

        print("post-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"post-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
