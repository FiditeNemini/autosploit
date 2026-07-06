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
    "fullReconAction",
    "subdomainRows",
    "portRows",
    "webHostRows",
    "crawlRows",
    "osintRows",
    "copySubdomains",
    "copyPorts",
    "copyWebHosts",
    "copyCrawl",
    "copyOSINT",
    "activityTelemetry",
]

REQUIRED_ROUTES = [
    "/qa/seed-recon-action-status",
    "/qa/seed-recon-copy-actions",
    "/qa/recon-copy",
]

REQUIRED_STATE_KEYS = [
    "reconAction",
    "reconCopyActions",
    "results.subdomains",
    "results.ports",
    "results.webHosts",
    "results.osint",
    "tabActivities",
    "feedRecent",
]

REQUIRED_PROOFS = [
    "recon-action-status-proof.py",
    "recon-copy-actions-proof.py",
    "visual-recon-action-proof.py",
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

        coverage = request("GET", "/qa/recon-coverage")
        if coverage.get("ok") is not True:
            raise AssertionError(f"recon coverage failed: {coverage}")
        if coverage.get("reconSurfaces") != REQUIRED_SURFACES:
            raise AssertionError(f"recon surface list mismatch: {coverage}")
        if coverage.get("reconSurfaceCount") != len(REQUIRED_SURFACES):
            raise AssertionError(f"recon surface count mismatch: {coverage}")
        if coverage.get("reconSurfaceParity") is not True:
            raise AssertionError(f"recon surface parity mismatch: {coverage}")
        if coverage.get("routes") != REQUIRED_ROUTES:
            raise AssertionError(f"recon route list mismatch: {coverage}")
        if coverage.get("routeCount") != len(REQUIRED_ROUTES):
            raise AssertionError(f"recon route count mismatch: {coverage}")
        if coverage.get("routeParity") is not True:
            raise AssertionError(f"recon route parity mismatch: {coverage}")
        if coverage.get("stateKeys") != REQUIRED_STATE_KEYS:
            raise AssertionError(f"recon state-key list mismatch: {coverage}")
        if coverage.get("stateKeyCount") != len(REQUIRED_STATE_KEYS):
            raise AssertionError(f"recon state-key count mismatch: {coverage}")
        if coverage.get("stateKeyParity") is not True:
            raise AssertionError(f"recon state-key parity mismatch: {coverage}")
        if coverage.get("proofs") != REQUIRED_PROOFS:
            raise AssertionError(f"recon proof list mismatch: {coverage}")
        if coverage.get("proofCount") != len(REQUIRED_PROOFS):
            raise AssertionError(f"recon proof count mismatch: {coverage}")
        if coverage.get("proofFileParity") is not True:
            raise AssertionError(f"recon proof-file parity mismatch: {coverage}")
        for contract in (
            "fullReconAction",
            "copyActions",
            "parsedReconResults",
            "activityTelemetry",
        ):
            if (coverage.get("contracts") or {}).get(contract) is not True:
                raise AssertionError(f"recon contract {contract} missing: {coverage}")

        state = request("GET", "/state")
        qa = state.get("qaCoverage") or {}
        if "/qa/recon-coverage" not in (qa.get("stateRoutes") or []):
            raise AssertionError(f"state route list missing recon coverage: {qa}")

        index = request("GET", "/qa/coverage-index", timeout=120.0)
        group = (index.get("groups") or {}).get("tabsAndSessions") or {}
        if group.get("reconSurfaces") != coverage.get("reconSurfaces"):
            raise AssertionError(f"coverage-index recon surface mirror mismatch: {index}")
        if group.get("reconSurfaceParity") != coverage.get("reconSurfaceParity"):
            raise AssertionError(f"coverage-index recon surface parity mismatch: {index}")
        if group.get("reconProofs") != coverage.get("proofs"):
            raise AssertionError(f"coverage-index recon proof mirror mismatch: {index}")
        if group.get("reconProofFileParity") != coverage.get("proofFileParity"):
            raise AssertionError(f"coverage-index recon proof-file parity mismatch: {index}")
        if group.get("reconStateKeys") != coverage.get("stateKeys"):
            raise AssertionError(f"coverage-index recon state-key mirror mismatch: {index}")
        if group.get("reconContracts") != coverage.get("contracts"):
            raise AssertionError(f"coverage-index recon contract mirror mismatch: {index}")

        print("recon-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"recon-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
