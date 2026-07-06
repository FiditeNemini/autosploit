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
ROUTE = "/qa/qwen-multimodal-promotion-readiness"
LOADER_PROOF = "live-qwen-multimodal-loader-proof.py"
LOADER_ARTIFACT = "docs/live-proofs/live-qwen-multimodal-loader-proof.json"


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


def assert_loader_harness_gate(payload: dict, gap: dict, index: dict) -> None:
    if payload.get("ok") is not True:
        raise AssertionError(f"{ROUTE} failed: {payload}")
    if not (ROOT / "scripts" / LOADER_PROOF).is_file():
        raise AssertionError(f"{LOADER_PROOF} must exist before the loader gate can progress")
    if payload.get("promotionGateMode") != "script-plus-live-result-artifact":
        raise AssertionError(f"{ROUTE} gate mode drifted: {payload}")
    if payload.get("promotionReady") is not False:
        raise AssertionError(f"{ROUTE} must not promote from script existence alone: {payload}")
    if payload.get("completionClaimAllowed") is not False:
        raise AssertionError(f"{ROUTE} must still block completion claims without the loader artifact: {payload}")

    proof_existence = payload.get("proofExistence") or {}
    if proof_existence.get(LOADER_PROOF) is not True:
        raise AssertionError(f"{ROUTE} must detect the loader proof script: {payload}")
    if LOADER_PROOF in (payload.get("missingLiveProofs") or []):
        raise AssertionError(f"{ROUTE} should not list the loader script as missing once it exists: {payload}")
    if LOADER_ARTIFACT not in (payload.get("missingLiveResultArtifacts") or []):
        raise AssertionError(f"{ROUTE} must still require the loader live result artifact: {payload}")
    if LOADER_PROOF in (payload.get("passingLiveProofs") or []):
        raise AssertionError(f"{ROUTE} must not report the loader proof as passing without artifact: {payload}")

    rows = {row.get("requiredProof"): row for row in payload.get("criteria") or []}
    loader = rows.get(LOADER_PROOF)
    if not loader:
        raise AssertionError(f"{ROUTE} missing loader criterion row: {payload}")
    if loader.get("scriptExists") is not True or loader.get("proofExists") is not True:
        raise AssertionError(f"{ROUTE} loader row must show the harness exists: {loader}")
    if loader.get("resultArtifact") != LOADER_ARTIFACT:
        raise AssertionError(f"{ROUTE} loader artifact path mismatch: {loader}")
    if loader.get("resultExists") is not False or loader.get("resultOK") is not False:
        raise AssertionError(f"{ROUTE} loader live result should still be absent at this checkpoint: {loader}")
    if loader.get("status") != "missing-live-result":
        raise AssertionError(f"{ROUTE} loader row should be gated on missing live result: {loader}")

    qwen_gap = (gap.get("gapContracts") or {}).get("qwenMultimodalRuntime") or {}
    if (qwen_gap.get("promotionProofExistence") or {}).get(LOADER_PROOF) is not True:
        raise AssertionError(f"gap ledger must detect loader proof script: {qwen_gap}")
    if (qwen_gap.get("promotionLiveResultOK") or {}).get(LOADER_PROOF) is not False:
        raise AssertionError(f"gap ledger must not treat missing loader artifact as ok: {qwen_gap}")
    if LOADER_ARTIFACT not in (qwen_gap.get("missingPromotionLiveResultArtifacts") or []):
        raise AssertionError(f"gap ledger must keep loader artifact missing: {qwen_gap}")

    app_state = (index.get("groups") or {}).get("appState") or {}
    if "qwen-multimodal-loader-harness-gate-proof.py" not in (app_state.get("proofs") or []):
        raise AssertionError(f"coverage index missing loader harness gate proof: {app_state}")
    if (app_state.get("qwenMultimodalPromotionProofExistence") or {}).get(LOADER_PROOF) is not True:
        raise AssertionError(f"coverage index must mirror loader script existence: {app_state}")
    if LOADER_ARTIFACT not in (app_state.get("qwenMultimodalMissingLiveResultArtifacts") or []):
        raise AssertionError(f"coverage index must mirror missing loader artifact: {app_state}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        payload = request("GET", ROUTE, timeout=45.0)
        gap = request("GET", "/qa/gap-ledger", timeout=45.0)
        index = request("GET", "/qa/coverage-index", timeout=120.0)
        assert_loader_harness_gate(payload, gap, index)
        print("qwen-multimodal-loader-harness-gate proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"qwen-multimodal-loader-harness-gate proof failed: {exc}", flush=True)
        raise SystemExit(1)
