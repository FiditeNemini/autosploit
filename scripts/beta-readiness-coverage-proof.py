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
APP = ROOT / "release" / "ExploitBot.app"
DMG = ROOT / "release" / "ExploitBot-beta.dmg"

EXPECTED_GATES = [
    "sourceProofMatrix",
    "visualArtifacts",
    "liveArtifacts",
    "checkpointLedger",
    "signedAppBundle",
    "signedDmg",
    "releaseManifest",
    "knownGapLedger",
    "notarizationProfile",
]

EXPECTED_STATUS = {
    "sourceProofMatrix": "ready",
    "visualArtifacts": "ready",
    "liveArtifacts": "ready",
    "checkpointLedger": "ready",
    "signedAppBundle": "ready",
    "signedDmg": "ready",
    "releaseManifest": "ready",
    "knownGapLedger": "ready-with-known-gaps",
    "notarizationProfile": "blocked-requires-profile",
}

EXPECTED_PROOFS = [
    "beta-readiness-coverage-proof.py",
    "release-readiness-proof.py",
    "artifact-ledger-proof.py",
    "audit-ledger-proof.py",
    "gap-ledger-proof.py",
    "coverage-index-proof.py",
    "app-qa-matrix-smoke-proof.py",
]

EXPECTED_ROUTES = [
    "/qa/beta-readiness-coverage",
    "/qa/release-readiness",
    "/qa/artifact-ledger",
    "/qa/audit-ledger",
    "/qa/gap-ledger",
    "/qa/coverage-index",
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


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def assert_codesign() -> None:
    app_result = run_cmd(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(APP)])
    if app_result.returncode != 0:
        raise AssertionError(f"release app codesign failed: {app_result.stdout}")
    dmg_result = run_cmd(["codesign", "--verify", "--verbose=2", str(DMG)])
    if dmg_result.returncode != 0:
        raise AssertionError(f"release DMG codesign failed: {dmg_result.stdout}")


def assert_payload(payload: dict) -> None:
    if payload.get("ok") is not True:
        raise AssertionError(f"beta readiness coverage route failed: {payload}")
    if payload.get("gates") != EXPECTED_GATES:
        raise AssertionError(f"beta readiness gate list mismatch: {payload}")
    if payload.get("gateCount") != len(EXPECTED_GATES):
        raise AssertionError(f"beta readiness gate count mismatch: {payload}")
    if payload.get("gateParity") is not True:
        raise AssertionError(f"beta readiness gate parity mismatch: {payload}")
    if payload.get("gateStatus") != EXPECTED_STATUS:
        raise AssertionError(f"beta readiness gate status mismatch: {payload}")
    if payload.get("readyGateCount") != 8:
        raise AssertionError(f"beta readiness ready gate count mismatch: {payload}")
    if payload.get("blockedGateCount") != 1:
        raise AssertionError(f"beta readiness blocked gate count mismatch: {payload}")
    if payload.get("packageReady") is not True:
        raise AssertionError(f"beta readiness should mark signed package ready: {payload}")
    if payload.get("distributionReady") is not False:
        raise AssertionError(f"beta readiness should not mark distribution ready before notarization: {payload}")
    if payload.get("notarizationGate") != "requires-notary-profile":
        raise AssertionError(f"beta readiness notarization gate mismatch: {payload}")
    if payload.get("notaryProfileRequired") is not True:
        raise AssertionError(f"beta readiness notary profile requirement mismatch: {payload}")
    if payload.get("knownGapCount", 0) < 1:
        raise AssertionError(f"beta readiness should surface known gaps: {payload}")

    if payload.get("routes") != EXPECTED_ROUTES:
        raise AssertionError(f"beta readiness route list mismatch: {payload}")
    if payload.get("routeCount") != len(EXPECTED_ROUTES):
        raise AssertionError(f"beta readiness route count mismatch: {payload}")
    if payload.get("routeParity") is not True:
        raise AssertionError(f"beta readiness route parity mismatch: {payload}")
    if payload.get("proofs") != EXPECTED_PROOFS:
        raise AssertionError(f"beta readiness proof list mismatch: {payload}")
    if payload.get("proofCount") != len(EXPECTED_PROOFS):
        raise AssertionError(f"beta readiness proof count mismatch: {payload}")
    if payload.get("proofFileParity") is not True:
        raise AssertionError(f"beta readiness proof-file parity mismatch: {payload}")
    missing_files = sorted(name for name in EXPECTED_PROOFS if not (ROOT / "scripts" / name).is_file())
    if missing_files:
        raise AssertionError(f"beta readiness names non-existent proof files: {missing_files}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        payload = request("GET", "/qa/beta-readiness-coverage")
        assert_payload(payload)
        assert_codesign()

        index = request("GET", "/qa/coverage-index")
        release_group = (index.get("groups") or {}).get("releaseReadiness") or {}
        if release_group.get("betaReadinessGates") != payload.get("gates"):
            raise AssertionError(f"coverage index beta readiness gates mismatch: {index}")
        if release_group.get("betaReadinessGateStatus") != payload.get("gateStatus"):
            raise AssertionError(f"coverage index beta readiness gate status mismatch: {index}")
        if release_group.get("betaReadinessProofFileParity") != payload.get("proofFileParity"):
            raise AssertionError(f"coverage index beta readiness proof parity mismatch: {index}")

        state = request("GET", "/state")
        if "/qa/beta-readiness-coverage" not in ((state.get("qaCoverage") or {}).get("stateRoutes") or []):
            raise AssertionError(f"state route list missing beta readiness route: {state.get('qaCoverage')}")

        print("beta-readiness-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"beta-readiness-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
