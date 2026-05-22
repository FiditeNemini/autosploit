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


def assert_audit_ledger() -> None:
    state = request("GET", "/state")
    proof = request("GET", "/qa/proof-ledger")
    artifact = request("GET", "/qa/artifact-ledger")
    checkpoint = request("GET", "/qa/checkpoint-ledger")
    gap = request("GET", "/qa/gap-ledger")
    audit = request("GET", "/qa/audit-ledger")

    if audit.get("ok") is not True:
        raise AssertionError(f"/qa/audit-ledger failed: {audit}")
    if audit.get("proofCount") != proof.get("proofCount"):
        raise AssertionError(f"audit proof count mismatch: {audit}")
    if audit.get("proofLedgerCategoryCounts") != proof.get("categoryCounts"):
        raise AssertionError(f"audit source proof category counts mismatch: {audit}")
    if audit.get("proofLedgerCategorySurfaces") != proof.get("categorySurfaces"):
        raise AssertionError(f"audit source proof category surfaces mismatch: {audit}")
    if audit.get("proofLedgerCategorySurfaceCount") != proof.get("categorySurfaceCount"):
        raise AssertionError(f"audit source proof category surface count mismatch: {audit}")
    if audit.get("proofLedgerCategoryOtherCount") != proof.get("categoryOtherCount"):
        raise AssertionError(f"audit source proof category other count mismatch: {audit}")
    if audit.get("proofLedgerCategoryTotalCount") != proof.get("categoryTotalCount"):
        raise AssertionError(f"audit source proof category total count mismatch: {audit}")
    if audit.get("proofLedgerCategoryParity") != proof.get("categoryParity"):
        raise AssertionError(f"audit source proof category parity mismatch: {audit}")
    expected_proof_categories = {
        name: category.get("count")
        for name, category in (proof.get("categories") or {}).items()
    }
    if audit.get("proofCategoryCounts") != expected_proof_categories:
        raise AssertionError(f"audit proof category counts mismatch: {audit}")
    core_proof_categories = {"agent", "chat", "context", "runtime", "settings", "tabs", "tools", "visual"}
    if audit.get("proofCategorySurfaces") != sorted(core_proof_categories):
        raise AssertionError(f"audit proof category surfaces mismatch: {audit}")
    if audit.get("proofCategorySurfaceCount") != len(core_proof_categories):
        raise AssertionError(f"audit proof category surface count mismatch: {audit}")
    if audit.get("proofCategoryTotalCount") != proof.get("proofCount"):
        raise AssertionError(f"audit proof category total mismatch: {audit}")
    if audit.get("proofCategoryParity") is not True:
        raise AssertionError(f"audit proof category parity mismatch: {audit}")
    if audit.get("visualManifestCount") != artifact.get("visualManifestCount"):
        raise AssertionError(f"audit visual manifest count mismatch: {audit}")
    if audit.get("visualCaptureCount") != artifact.get("visualCaptureCount"):
        raise AssertionError(f"audit visual capture count mismatch: {audit}")
    if audit.get("missingVisualCaptureCount") != len(artifact.get("missingVisualCaptures") or []):
        raise AssertionError(f"audit missing visual count mismatch: {audit}")
    if audit.get("missingVisualCaptures") != artifact.get("missingVisualCaptures"):
        raise AssertionError(f"audit missing visual list mismatch: {audit}")
    if audit.get("liveProofCount") != artifact.get("liveProofCount"):
        raise AssertionError(f"audit live proof count mismatch: {audit}")
    if audit.get("liveProofOkCount") != artifact.get("liveProofOkCount"):
        raise AssertionError(f"audit live proof ok count mismatch: {audit}")
    if audit.get("failedLiveProofCount") != len(artifact.get("failedLiveProofs") or []):
        raise AssertionError(f"audit failed live proof count mismatch: {audit}")
    if audit.get("failedLiveProofs") != artifact.get("failedLiveProofs"):
        raise AssertionError(f"audit failed live proof list mismatch: {audit}")
    if audit.get("checkpointCount") != checkpoint.get("checkpointCount"):
        raise AssertionError(f"audit checkpoint count mismatch: {audit}")
    if audit.get("completeCheckpointCount") != checkpoint.get("completeCheckpointCount"):
        raise AssertionError(f"audit complete checkpoint count mismatch: {audit}")
    if audit.get("checkpointCompletionRatio") != checkpoint.get("checkpointCompletionRatio"):
        raise AssertionError(f"audit checkpoint completion ratio mismatch: {audit}")
    if audit.get("completeCheckpoints") != checkpoint.get("completeCheckpoints"):
        raise AssertionError(f"audit complete checkpoint list mismatch: {audit}")
    if audit.get("incompleteCheckpointCount") != len(checkpoint.get("incompleteCheckpoints") or []):
        raise AssertionError(f"audit incomplete checkpoint count mismatch: {audit}")
    if audit.get("incompleteCheckpoints") != checkpoint.get("incompleteCheckpoints"):
        raise AssertionError(f"audit incomplete checkpoint list mismatch: {audit}")
    if audit.get("latestCheckpoint") != checkpoint.get("latestCheckpoint"):
        raise AssertionError(f"audit latest checkpoint mismatch: {audit}")
    if audit.get("latestCheckpointNumber") != checkpoint.get("latestCheckpointNumber"):
        raise AssertionError(f"audit latest checkpoint number mismatch: {audit}")
    if audit.get("currentGapCount") != gap.get("currentGapCount"):
        raise AssertionError(f"audit current gap count mismatch: {audit}")
    if audit.get("nextGap") != gap.get("nextGap"):
        raise AssertionError(f"audit next gap mismatch: {audit}")
    if audit.get("openGapIds") != gap.get("openGapIds"):
        raise AssertionError(f"audit open gap ids mismatch: {audit}")
    if audit.get("gapContracts") != gap.get("gapContracts"):
        raise AssertionError(f"audit gap contracts mismatch: {audit}")

    qa = state.get("qaCoverage") or {}
    if "/qa/audit-ledger" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing audit-ledger route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_audit_ledger()
        print("audit-ledger proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"audit-ledger proof failed: {exc}", flush=True)
        raise SystemExit(1)
