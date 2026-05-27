#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
SYSTEM_REVIEW = ROOT / "docs" / "app-system-review-2026-05-21.md"

EXPECTED_QWEN_PROMOTION_CRITERIA = [
    {
        "id": "qwenMultimodalLoader",
        "status": "missing",
        "requiredProof": "live-qwen-multimodal-loader-proof.py",
    },
    {
        "id": "prefixCacheKeyDiscipline",
        "status": "missing",
        "requiredProof": "live-qwen-multimodal-prefix-cache-proof.py",
    },
    {
        "id": "multimodalContextPacketRouting",
        "status": "missing",
        "requiredProof": "live-qwen-multimodal-context-routing-proof.py",
    },
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


def documented_current_gaps() -> list[str]:
    text = SYSTEM_REVIEW.read_text(encoding="utf-8")
    match = re.search(r"## Current Gaps To Close Next\n\n(?P<body>.*)$", text, flags=re.S)
    if not match:
        raise AssertionError("system review is missing Current Gaps To Close Next")
    body = match.group("body")
    gaps = []
    current: list[str] = []
    for line in body.splitlines():
        if re.match(r"^\d+\. ", line):
            if current:
                gaps.append(" ".join(current))
            current = [re.sub(r"^\d+\. ", "", line).strip()]
        elif current and (line.startswith("   ") or not line.strip()):
            if line.strip():
                current.append(line.strip())
    if current:
        gaps.append(" ".join(current))
    return gaps


def assert_gap_ledger() -> None:
    state = request("GET", "/state")
    ledger = request("GET", "/qa/gap-ledger")
    expected_gaps = documented_current_gaps()

    if ledger.get("ok") is not True:
        raise AssertionError(f"/qa/gap-ledger failed: {ledger}")
    if ledger.get("source") != "docs/app-system-review-2026-05-21.md#current-gaps-to-close-next":
        raise AssertionError(f"gap ledger source mismatch: {ledger}")
    if ledger.get("sourceDerived") is not True:
        raise AssertionError(f"gap ledger should be derived from the source document: {ledger}")
    if ledger.get("sourcePathExists") is not True:
        raise AssertionError(f"gap ledger source path should exist: {ledger}")
    if ledger.get("currentGapCount") != len(expected_gaps):
        raise AssertionError(f"gap ledger count mismatch expected {len(expected_gaps)}: {ledger}")
    if ledger.get("currentGaps") != expected_gaps:
        raise AssertionError(f"gap ledger current gaps mismatch expected {expected_gaps}: {ledger}")
    if ledger.get("unsupportedMultimodalBlocked") is not False:
        raise AssertionError(f"gap ledger should record Qwen VL as no longer hard-blocked: {ledger}")
    if set(ledger.get("supportedFamilies") or []) != {"qwen", "minimax", "zaya"}:
        raise AssertionError(f"gap ledger supported families mismatch: {ledger}")
    if "qwenMultimodalRuntime" not in (ledger.get("openGapIds") or []):
        raise AssertionError(f"gap ledger missing qwen multimodal gap id: {ledger}")
    if ledger.get("openGapCount") != len(ledger.get("openGapIds") or []):
        raise AssertionError(f"gap ledger open gap count mismatch: {ledger}")
    if ledger.get("gapContractCount") != len(ledger.get("gapContracts") or {}):
        raise AssertionError(f"gap ledger contract count mismatch: {ledger}")
    qwen_gap = (ledger.get("gapContracts") or {}).get("qwenMultimodalRuntime") or {}
    if qwen_gap.get("status") != "in_progress":
        raise AssertionError(f"qwen multimodal gap should be in_progress: {ledger}")
    if qwen_gap.get("supportedFamilies") != ["qwen", "minimax"]:
        raise AssertionError(f"qwen multimodal gap supported families mismatch: {qwen_gap}")
    if set(qwen_gap.get("blockedModelKinds") or []) != set():
        raise AssertionError(f"qwen multimodal blocked kinds should be empty while in progress: {qwen_gap}")
    if ledger.get("qwenMultimodalBlockedModelKindCount") != len(qwen_gap.get("blockedModelKinds") or []):
        raise AssertionError(f"qwen multimodal blocked model kind count mismatch: {ledger}")
    if ledger.get("qwenMultimodalRequiredRuntimeWorkCount") != len(qwen_gap.get("requiredRuntimeWork") or []):
        raise AssertionError(f"qwen multimodal required runtime work count mismatch: {ledger}")
    if ledger.get("qwenMultimodalProofCount") != len(qwen_gap.get("proofs") or []):
        raise AssertionError(f"qwen multimodal proof count mismatch: {ledger}")
    missing_proof_files = sorted(
        proof for proof in qwen_gap.get("proofs") or []
        if not (ROOT / "scripts" / proof).is_file()
    )
    if missing_proof_files:
        raise AssertionError(f"qwen multimodal gap names missing proof files: {missing_proof_files}")
    if ledger.get("qwenMultimodalProofFileParity") is not True:
        raise AssertionError(f"qwen multimodal proof-file parity mismatch: {ledger}")
    promotion_criteria = qwen_gap.get("promotionCriteria") or []
    if qwen_gap.get("promotionReady") is not False:
        raise AssertionError(f"qwen multimodal promotion should remain false until live proofs exist: {qwen_gap}")
    if qwen_gap.get("promotionCriteriaCount") != len(EXPECTED_QWEN_PROMOTION_CRITERIA):
        raise AssertionError(f"qwen multimodal promotion criteria count mismatch: {qwen_gap}")
    if qwen_gap.get("missingPromotionCriteriaIds") != [item["id"] for item in EXPECTED_QWEN_PROMOTION_CRITERIA]:
        raise AssertionError(f"qwen multimodal missing criteria id mismatch: {qwen_gap}")
    if qwen_gap.get("missingPromotionProofs") != [item["requiredProof"] for item in EXPECTED_QWEN_PROMOTION_CRITERIA]:
        raise AssertionError(f"qwen multimodal missing promotion proof mismatch: {qwen_gap}")
    expected_promotion_proof_existence = {
        item["requiredProof"]: False for item in EXPECTED_QWEN_PROMOTION_CRITERIA
    }
    if qwen_gap.get("promotionProofExistence") != expected_promotion_proof_existence:
        raise AssertionError(f"qwen multimodal promotion proof existence map mismatch: {qwen_gap}")
    if qwen_gap.get("promotionProofExistenceCount") != len(expected_promotion_proof_existence):
        raise AssertionError(f"qwen multimodal promotion proof existence count mismatch: {qwen_gap}")
    if qwen_gap.get("promotionProofExistenceParity") is not True:
        raise AssertionError(f"qwen multimodal promotion proof existence parity mismatch: {qwen_gap}")
    if ledger.get("qwenMultimodalPromotionReady") != qwen_gap.get("promotionReady"):
        raise AssertionError(f"gap ledger top-level qwen promotion readiness mismatch: {ledger}")
    if ledger.get("qwenMultimodalPromotionCriteriaCount") != qwen_gap.get("promotionCriteriaCount"):
        raise AssertionError(f"gap ledger top-level qwen promotion criteria count mismatch: {ledger}")
    if ledger.get("qwenMultimodalMissingPromotionCriteriaIds") != qwen_gap.get("missingPromotionCriteriaIds"):
        raise AssertionError(f"gap ledger top-level qwen missing criteria id mismatch: {ledger}")
    if ledger.get("qwenMultimodalMissingPromotionProofs") != qwen_gap.get("missingPromotionProofs"):
        raise AssertionError(f"gap ledger top-level qwen missing promotion proof mismatch: {ledger}")
    if ledger.get("qwenMultimodalPromotionProofExistence") != qwen_gap.get("promotionProofExistence"):
        raise AssertionError(f"gap ledger top-level qwen promotion proof existence mismatch: {ledger}")
    if ledger.get("qwenMultimodalPromotionProofExistenceCount") != qwen_gap.get("promotionProofExistenceCount"):
        raise AssertionError(f"gap ledger top-level qwen promotion proof existence count mismatch: {ledger}")
    if ledger.get("qwenMultimodalPromotionProofExistenceParity") != qwen_gap.get("promotionProofExistenceParity"):
        raise AssertionError(f"gap ledger top-level qwen promotion proof existence parity mismatch: {ledger}")
    for expected, actual in zip(EXPECTED_QWEN_PROMOTION_CRITERIA, promotion_criteria):
        for key, value in expected.items():
            if actual.get(key) != value:
                raise AssertionError(f"qwen multimodal promotion criterion {key} mismatch: {qwen_gap}")
        if (ROOT / "scripts" / expected["requiredProof"]).exists():
            raise AssertionError(f"qwen multimodal promotion proof unexpectedly exists before runtime support: {expected}")
    required_proofs = {
        "model-folder-warning-proof.py",
        "unsupported-model-start-proof.py",
        "qwen-multimodal-start-proof.py",
        "qwen-multimodal-runtime-blocker-proof.py",
    }
    if not required_proofs.issubset(set(qwen_gap.get("proofs") or [])):
        raise AssertionError(f"qwen multimodal gap missing enforcement proofs: {qwen_gap}")
    if ledger.get("nextGap") != expected_gaps[0]:
        raise AssertionError(f"gap ledger next gap mismatch: {ledger}")

    qa = state.get("qaCoverage") or {}
    if "/qa/gap-ledger" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing gap-ledger route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_gap_ledger()
        print("gap-ledger proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"gap-ledger proof failed: {exc}", flush=True)
        raise SystemExit(1)
