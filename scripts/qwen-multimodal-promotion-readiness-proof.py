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
PROOF = "qwen-multimodal-promotion-readiness-proof.py"

EXPECTED_CRITERIA = [
    "qwenMultimodalLoader",
    "prefixCacheKeyDiscipline",
    "multimodalContextPacketRouting",
]

EXPECTED_LIVE_PROOFS = [
    "live-qwen-multimodal-loader-proof.py",
    "live-qwen-multimodal-prefix-cache-proof.py",
    "live-qwen-multimodal-context-routing-proof.py",
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


def assert_payload(payload: dict, state: dict, index: dict, gap: dict) -> None:
    if payload.get("ok") is not True:
        raise AssertionError(f"{ROUTE} failed: {payload}")
    if payload.get("route") != ROUTE:
        raise AssertionError(f"{ROUTE} route mismatch: {payload}")
    if payload.get("proofLevel") != "qwen-multimodal-promotion-readiness-boundary":
        raise AssertionError(f"{ROUTE} proof level mismatch: {payload}")
    if payload.get("supportedFamilies") != ["qwen", "minimax"]:
        raise AssertionError(f"{ROUTE} active family scope mismatch: {payload}")
    if payload.get("inactiveFamilyPolicy") != "zaya-and-non-qwen-minimax-remain-outside-beta-lane":
        raise AssertionError(f"{ROUTE} inactive family policy mismatch: {payload}")
    if payload.get("promotionReady") is not False:
        raise AssertionError(f"{ROUTE} must not promote without live proofs: {payload}")
    if payload.get("completionClaimAllowed") is not False:
        raise AssertionError(f"{ROUTE} must block completion claims while live proofs are missing: {payload}")

    criteria = payload.get("criteria") or []
    if [row.get("id") for row in criteria] != EXPECTED_CRITERIA:
        raise AssertionError(f"{ROUTE} criteria order mismatch: {payload}")
    if payload.get("criteriaCount") != len(EXPECTED_CRITERIA):
        raise AssertionError(f"{ROUTE} criteria count mismatch: {payload}")
    if payload.get("requiredLiveProofs") != EXPECTED_LIVE_PROOFS:
        raise AssertionError(f"{ROUTE} live proof list mismatch: {payload}")
    if payload.get("requiredLiveProofCount") != len(EXPECTED_LIVE_PROOFS):
        raise AssertionError(f"{ROUTE} live proof count mismatch: {payload}")
    if payload.get("proofExistenceParity") is not True:
        raise AssertionError(f"{ROUTE} proof existence parity mismatch: {payload}")
    if payload.get("missingLiveProofs") != EXPECTED_LIVE_PROOFS:
        raise AssertionError(f"{ROUTE} should list the missing live proofs exactly: {payload}")
    if payload.get("missingLiveProofCount") != len(EXPECTED_LIVE_PROOFS):
        raise AssertionError(f"{ROUTE} missing live proof count mismatch: {payload}")
    if payload.get("provenLiveProofs") != []:
        raise AssertionError(f"{ROUTE} should not report proven live Qwen multimodal proofs yet: {payload}")

    proof_existence = payload.get("proofExistence") or {}
    if sorted(proof_existence) != sorted(EXPECTED_LIVE_PROOFS):
        raise AssertionError(f"{ROUTE} proof existence keys mismatch: {payload}")
    if any(proof_existence.get(name) is not False for name in EXPECTED_LIVE_PROOFS):
        raise AssertionError(f"{ROUTE} live proof files should still be absent at this checkpoint: {payload}")

    for row in criteria:
        if row.get("status") != "missing-live-proof":
            raise AssertionError(f"{ROUTE} criteria should be live-proof gated: {row}")
        if row.get("requiredProof") not in EXPECTED_LIVE_PROOFS:
            raise AssertionError(f"{ROUTE} criterion required proof mismatch: {row}")
        if row.get("proofExists") is not False:
            raise AssertionError(f"{ROUTE} criterion proof existence mismatch: {row}")
        if not row.get("proofCommand", "").startswith("python3 scripts/live-qwen-multimodal-"):
            raise AssertionError(f"{ROUTE} criterion proof command missing: {row}")

    if payload.get("gapLedgerOpenGapIds") != ["qwenMultimodalRuntime"]:
        raise AssertionError(f"{ROUTE} gap ledger open IDs mismatch: {payload}")
    if payload.get("gapLedgerPromotionReady") != gap.get("qwenMultimodalPromotionReady"):
        raise AssertionError(f"{ROUTE} gap ledger promotion mirror mismatch: {payload}")
    if payload.get("gapLedgerMissingPromotionProofs") != gap.get("qwenMultimodalMissingPromotionProofs"):
        raise AssertionError(f"{ROUTE} gap ledger missing proof mirror mismatch: {payload}")

    routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
    if ROUTE not in routes:
        raise AssertionError(f"/state qaCoverage missing {ROUTE}: {state.get('qaCoverage')}")

    app_state_group = (index.get("groups") or {}).get("appState") or {}
    if ROUTE not in (app_state_group.get("endpoints") or []):
        raise AssertionError(f"/qa/coverage-index appState missing {ROUTE}: {app_state_group}")
    if PROOF not in (app_state_group.get("proofs") or []):
        raise AssertionError(f"/qa/coverage-index appState missing proof: {app_state_group}")
    if app_state_group.get("qwenMultimodalPromotionReadinessReady") != payload.get("promotionReady"):
        raise AssertionError(f"/qa/coverage-index promotion readiness mirror mismatch: {app_state_group}")
    if app_state_group.get("qwenMultimodalPromotionReadinessMissingLiveProofs") != payload.get("missingLiveProofs"):
        raise AssertionError(f"/qa/coverage-index missing live proof mirror mismatch: {app_state_group}")
    if app_state_group.get("qwenMultimodalPromotionReadinessProofExistenceParity") != payload.get("proofExistenceParity"):
        raise AssertionError(f"/qa/coverage-index proof parity mirror mismatch: {app_state_group}")


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
        state = request("GET", "/state")
        index = request("GET", "/qa/coverage-index", timeout=45.0)
        gap = request("GET", "/qa/gap-ledger")
        assert_payload(payload, state, index, gap)
        print("qwen-multimodal-promotion-readiness proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"qwen-multimodal-promotion-readiness proof failed: {exc}", flush=True)
        raise SystemExit(1)
