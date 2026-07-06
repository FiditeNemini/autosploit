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
PROOF = "qwen-multimodal-live-result-gate-proof.py"

EXPECTED_LIVE_PROOFS = [
    "live-qwen-multimodal-loader-proof.py",
    "live-qwen-multimodal-prefix-cache-proof.py",
    "live-qwen-multimodal-context-routing-proof.py",
]
EXPECTED_ARTIFACTS = {
    proof: f"docs/live-proofs/{proof.removesuffix('.py')}.json"
    for proof in EXPECTED_LIVE_PROOFS
}
EXPECTED_SCRIPT_EXISTENCE = {
    "live-qwen-multimodal-loader-proof.py": True,
    "live-qwen-multimodal-prefix-cache-proof.py": False,
    "live-qwen-multimodal-context-routing-proof.py": False,
}


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


def assert_live_result_gate(payload: dict, gap: dict, index: dict) -> None:
    if payload.get("ok") is not True:
        raise AssertionError(f"{ROUTE} failed: {payload}")
    if payload.get("promotionGateMode") != "script-plus-live-result-artifact":
        raise AssertionError(f"{ROUTE} must gate promotion on script plus live result artifact: {payload}")
    if payload.get("promotionReadyRequiresLiveResults") is not True:
        raise AssertionError(f"{ROUTE} must require live result artifacts before promotion: {payload}")
    if payload.get("promotionReady") is not False:
        raise AssertionError(f"{ROUTE} must stay false without live result artifacts: {payload}")
    if payload.get("completionClaimAllowed") is not False:
        raise AssertionError(f"{ROUTE} must block completion claims without live result artifacts: {payload}")
    if payload.get("requiredLiveProofs") != EXPECTED_LIVE_PROOFS:
        raise AssertionError(f"{ROUTE} live proof list drifted: {payload}")
    if payload.get("requiredLiveResultArtifacts") != EXPECTED_ARTIFACTS:
        raise AssertionError(f"{ROUTE} live artifact map drifted: {payload}")
    if payload.get("requiredLiveResultArtifactCount") != len(EXPECTED_ARTIFACTS):
        raise AssertionError(f"{ROUTE} artifact count mismatch: {payload}")
    if payload.get("liveResultArtifactParity") is not True:
        raise AssertionError(f"{ROUTE} live result artifact parity mismatch: {payload}")

    results = payload.get("liveProofResults") or []
    if [row.get("requiredProof") for row in results] != EXPECTED_LIVE_PROOFS:
        raise AssertionError(f"{ROUTE} live result rows mismatch: {payload}")
    if payload.get("liveProofResultCount") != len(EXPECTED_LIVE_PROOFS):
        raise AssertionError(f"{ROUTE} live result count mismatch: {payload}")
    if payload.get("passingLiveProofs") != []:
        raise AssertionError(f"{ROUTE} must not report passing Qwen VL proofs at this checkpoint: {payload}")
    if payload.get("passingLiveProofCount") != 0:
        raise AssertionError(f"{ROUTE} passing proof count mismatch: {payload}")
    if payload.get("missingLiveResultArtifacts") != list(EXPECTED_ARTIFACTS.values()):
        raise AssertionError(f"{ROUTE} missing live result artifacts mismatch: {payload}")
    if payload.get("missingLiveResultArtifactCount") != len(EXPECTED_ARTIFACTS):
        raise AssertionError(f"{ROUTE} missing live result count mismatch: {payload}")

    for row in results:
        proof = row.get("requiredProof")
        if row.get("resultArtifact") != EXPECTED_ARTIFACTS.get(proof):
            raise AssertionError(f"{ROUTE} result artifact mismatch: {row}")
        expected_script_exists = EXPECTED_SCRIPT_EXISTENCE[proof]
        if row.get("scriptExists") is not expected_script_exists:
            raise AssertionError(f"{ROUTE} live script existence mismatch at this checkpoint: {row}")
        if row.get("resultExists") is not False:
            raise AssertionError(f"{ROUTE} live result should still be absent at this checkpoint: {row}")
        if row.get("resultOK") is not False:
            raise AssertionError(f"{ROUTE} absent live result must not be treated as ok: {row}")
        expected_status = "missing-live-result" if expected_script_exists else "missing-live-proof"
        if row.get("status") != expected_status:
            raise AssertionError(f"{ROUTE} live result status mismatch: {row}")

    qwen_gap = (gap.get("gapContracts") or {}).get("qwenMultimodalRuntime") or {}
    if qwen_gap.get("promotionGateMode") != payload.get("promotionGateMode"):
        raise AssertionError(f"gap ledger promotion gate mode mismatch: {qwen_gap}")
    if qwen_gap.get("promotionReadyRequiresLiveResults") is not True:
        raise AssertionError(f"gap ledger must require live result artifacts: {qwen_gap}")
    if qwen_gap.get("promotionLiveResultArtifacts") != EXPECTED_ARTIFACTS:
        raise AssertionError(f"gap ledger live artifact map mismatch: {qwen_gap}")
    if qwen_gap.get("promotionLiveResultArtifactParity") is not True:
        raise AssertionError(f"gap ledger live artifact parity mismatch: {qwen_gap}")
    if qwen_gap.get("passingPromotionProofs") != []:
        raise AssertionError(f"gap ledger must not report passing Qwen VL proofs yet: {qwen_gap}")
    if gap.get("qwenMultimodalPromotionLiveResultArtifacts") != EXPECTED_ARTIFACTS:
        raise AssertionError(f"top-level gap ledger live artifact map mismatch: {gap}")
    if gap.get("qwenMultimodalPassingPromotionProofs") != []:
        raise AssertionError(f"top-level gap ledger must not report passing Qwen VL proofs yet: {gap}")

    app_state_group = (index.get("groups") or {}).get("appState") or {}
    if PROOF not in (app_state_group.get("proofs") or []):
        raise AssertionError(f"/qa/coverage-index appState missing {PROOF}: {app_state_group}")
    if app_state_group.get("qwenMultimodalPromotionGateMode") != payload.get("promotionGateMode"):
        raise AssertionError(f"coverage index gate mode mirror mismatch: {app_state_group}")
    if app_state_group.get("qwenMultimodalPromotionReadyRequiresLiveResults") is not True:
        raise AssertionError(f"coverage index must mirror live result requirement: {app_state_group}")
    if app_state_group.get("qwenMultimodalMissingLiveResultArtifacts") != payload.get("missingLiveResultArtifacts"):
        raise AssertionError(f"coverage index missing live result mirror mismatch: {app_state_group}")


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
        assert_live_result_gate(payload, gap, index)
        print("qwen-multimodal-live-result-gate proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"qwen-multimodal-live-result-gate proof failed: {exc}", flush=True)
        raise SystemExit(1)
