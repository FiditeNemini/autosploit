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
    "findingCrud",
    "reportPreview",
    "artifactExport",
    "agentDraft",
    "activityFeed",
    "durableFindingStore",
    "contextHandoff",
]

REQUIRED_PROOFS = [
    "report-generate-action-proof.py",
    "report-finding-actions-proof.py",
    "report-visible-delete-wiring-proof.py",
    "report-export-proof.py",
    "report-visible-export-actions-proof.py",
    "report-agent-action-proof.py",
    "finding-wizard-submit-proof.py",
]

REQUIRED_STATE_KEYS = [
    "reportRenderActions",
    "reportFindingActions",
    "reportAction",
    "reportExport",
    "findings",
    "feedRecent",
    "contextCatalog",
]

REQUIRED_ROUTES = [
    "/qa/seed-report-generate-action",
    "/qa/report-generate-action",
    "/qa/seed-report-finding-actions",
    "/qa/report-create-finding",
    "/qa/report-submit-finding",
    "/qa/report-delete-finding",
    "/qa/seed-report-export",
    "/qa/report-export-action",
    "/qa/seed-report-agent-action",
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

        coverage = request("GET", "/qa/report-coverage")
        if coverage.get("ok") is not True:
            raise AssertionError(f"report coverage failed: {coverage}")
        if coverage.get("reportSurfaces") != REQUIRED_SURFACES:
            raise AssertionError(f"report surface list mismatch: {coverage}")
        if coverage.get("reportSurfaceCount") != len(REQUIRED_SURFACES):
            raise AssertionError(f"report surface count mismatch: {coverage}")
        if coverage.get("reportSurfaceParity") is not True:
            raise AssertionError(f"report surface parity mismatch: {coverage}")
        if coverage.get("proofs") != REQUIRED_PROOFS:
            raise AssertionError(f"report proof list mismatch: {coverage}")
        if coverage.get("proofCount") != len(REQUIRED_PROOFS):
            raise AssertionError(f"report proof count mismatch: {coverage}")
        if coverage.get("proofFileParity") is not True:
            raise AssertionError(f"report proof-file parity mismatch: {coverage}")
        if coverage.get("stateKeys") != REQUIRED_STATE_KEYS:
            raise AssertionError(f"report state keys mismatch: {coverage}")
        if coverage.get("stateKeyCount") != len(REQUIRED_STATE_KEYS):
            raise AssertionError(f"report state-key count mismatch: {coverage}")
        if coverage.get("stateKeyParity") is not True:
            raise AssertionError(f"report state-key parity mismatch: {coverage}")
        if coverage.get("routes") != REQUIRED_ROUTES:
            raise AssertionError(f"report routes mismatch: {coverage}")
        if coverage.get("routeCount") != len(REQUIRED_ROUTES):
            raise AssertionError(f"report route count mismatch: {coverage}")
        for contract in ("savedFindings", "reportArtifacts", "agentDraft", "contextHandoff", "activityTelemetry"):
            if (coverage.get("contracts") or {}).get(contract) is not True:
                raise AssertionError(f"report contract {contract} missing: {coverage}")

        state = request("GET", "/state")
        qa = state.get("qaCoverage") or {}
        if "/qa/report-coverage" not in (qa.get("stateRoutes") or []):
            raise AssertionError(f"state route list missing report coverage: {qa}")

        index = request("GET", "/qa/coverage-index")
        group = (index.get("groups") or {}).get("tabsAndSessions") or {}
        if group.get("reportSurfaces") != coverage.get("reportSurfaces"):
            raise AssertionError(f"coverage-index report surface mirror mismatch: {index}")
        if group.get("reportSurfaceParity") != coverage.get("reportSurfaceParity"):
            raise AssertionError(f"coverage-index report surface parity mismatch: {index}")
        if group.get("reportProofs") != coverage.get("proofs"):
            raise AssertionError(f"coverage-index report proof mirror mismatch: {index}")
        if group.get("reportProofFileParity") != coverage.get("proofFileParity"):
            raise AssertionError(f"coverage-index report proof-file parity mismatch: {index}")
        if group.get("reportStateKeys") != coverage.get("stateKeys"):
            raise AssertionError(f"coverage-index report state-key mirror mismatch: {index}")

        print("report-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"report-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
