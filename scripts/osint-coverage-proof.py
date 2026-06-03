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
    "usernameRows",
    "emailRows",
    "metadataRows",
    "screenshotArtifacts",
    "copyUsername",
    "copyEmail",
    "copyMetadata",
    "copyScreenshots",
    "copyAll",
    "artifactActions",
    "lifecycleTelemetry",
    "activityTelemetry",
]

REQUIRED_ROUTES = [
    "/qa/seed-osint-screenshot-artifact",
    "/qa/seed-osint-copy-actions",
    "/qa/osint-copy",
    "/qa/osint-artifact-action",
]

REQUIRED_STATE_KEYS = [
    "osintLifecycle",
    "osintArtifacts",
    "osintArtifactAction",
    "osintCopyActions",
    "results.osint",
    "tabActivities",
    "feedRecent",
]

REQUIRED_PROOFS = [
    "osint-screenshot-artifact-proof.py",
    "osint-copy-actions-proof.py",
    "osint-artifact-actions-proof.py",
    "visual-osint-screenshot-proof.py",
    "visual-osint-artifact-actions-proof.py",
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

        coverage = request("GET", "/qa/osint-coverage")
        if coverage.get("ok") is not True:
            raise AssertionError(f"osint coverage failed: {coverage}")
        if coverage.get("osintSurfaces") != REQUIRED_SURFACES:
            raise AssertionError(f"osint surface list mismatch: {coverage}")
        if coverage.get("osintSurfaceCount") != len(REQUIRED_SURFACES):
            raise AssertionError(f"osint surface count mismatch: {coverage}")
        if coverage.get("osintSurfaceParity") is not True:
            raise AssertionError(f"osint surface parity mismatch: {coverage}")
        if coverage.get("routes") != REQUIRED_ROUTES:
            raise AssertionError(f"osint route list mismatch: {coverage}")
        if coverage.get("routeCount") != len(REQUIRED_ROUTES):
            raise AssertionError(f"osint route count mismatch: {coverage}")
        if coverage.get("routeParity") is not True:
            raise AssertionError(f"osint route parity mismatch: {coverage}")
        if coverage.get("stateKeys") != REQUIRED_STATE_KEYS:
            raise AssertionError(f"osint state-key list mismatch: {coverage}")
        if coverage.get("stateKeyCount") != len(REQUIRED_STATE_KEYS):
            raise AssertionError(f"osint state-key count mismatch: {coverage}")
        if coverage.get("stateKeyParity") is not True:
            raise AssertionError(f"osint state-key parity mismatch: {coverage}")
        if coverage.get("proofs") != REQUIRED_PROOFS:
            raise AssertionError(f"osint proof list mismatch: {coverage}")
        if coverage.get("proofCount") != len(REQUIRED_PROOFS):
            raise AssertionError(f"osint proof count mismatch: {coverage}")
        if coverage.get("proofFileParity") is not True:
            raise AssertionError(f"osint proof-file parity mismatch: {coverage}")
        for contract in (
            "parsedOSINTRows",
            "screenshotArtifacts",
            "copyActions",
            "artifactActions",
            "lifecycleTelemetry",
            "activityTelemetry",
        ):
            if (coverage.get("contracts") or {}).get(contract) is not True:
                raise AssertionError(f"osint contract {contract} missing: {coverage}")

        state = request("GET", "/state")
        qa = state.get("qaCoverage") or {}
        if "/qa/osint-coverage" not in (qa.get("stateRoutes") or []):
            raise AssertionError(f"state route list missing osint coverage: {qa}")

        index = request("GET", "/qa/coverage-index")
        group = (index.get("groups") or {}).get("tabsAndSessions") or {}
        if group.get("osintSurfaces") != coverage.get("osintSurfaces"):
            raise AssertionError(f"coverage-index osint surface mirror mismatch: {index}")
        if group.get("osintSurfaceParity") != coverage.get("osintSurfaceParity"):
            raise AssertionError(f"coverage-index osint surface parity mismatch: {index}")
        if group.get("osintProofs") != coverage.get("proofs"):
            raise AssertionError(f"coverage-index osint proof mirror mismatch: {index}")
        if group.get("osintProofFileParity") != coverage.get("proofFileParity"):
            raise AssertionError(f"coverage-index osint proof-file parity mismatch: {index}")
        if group.get("osintStateKeys") != coverage.get("stateKeys"):
            raise AssertionError(f"coverage-index osint state-key mirror mismatch: {index}")
        if group.get("osintContracts") != coverage.get("contracts"):
            raise AssertionError(f"coverage-index osint contract mirror mismatch: {index}")

        print("osint-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"osint-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
