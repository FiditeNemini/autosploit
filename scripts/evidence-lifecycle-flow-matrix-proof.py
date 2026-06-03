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
DOCS = [
    ROOT / "docs" / "app-system-review-2026-05-21.md",
    ROOT / "docs" / "app-flow-inventory-2026-05-21.md",
]

EXPECTED_PROOFS = [
    "evidence-lifecycle-flow-matrix-proof.py",
    "evidence-lifecycle-coverage-proof.py",
    "result-parser-routing-proof.py",
    "result-context-catalog-proof.py",
    "context-flow-matrix-proof.py",
    "report-generate-action-proof.py",
    "report-export-proof.py",
    "stash-actions-proof.py",
    "coverage-index-proof.py",
    "app-qa-matrix-smoke-proof.py",
]


def request(method: str, path: str, body: str | dict | None = None, timeout: float = 45.0):
    if isinstance(body, dict):
        body = json.dumps(body)
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


def assert_file_proofs_exist(proofs: list[str], label: str) -> None:
    missing = [proof for proof in proofs if not (ROOT / "scripts" / proof).is_file()]
    if missing:
        raise AssertionError(f"{label} names missing proof files: {missing}")


def assert_rows(rows: list[dict], key: str, expected: list[str], coverage: dict, label: str) -> None:
    if [row.get(key) for row in rows] != expected:
        raise AssertionError(f"{label} row order mismatch: {rows}")
    for row in rows:
        name = row.get(key)
        proofs = row.get("proofs") or []
        routes = row.get("routes") or []
        if row.get("coverageRoute") != "/qa/evidence-lifecycle-coverage":
            raise AssertionError(f"{label} {name} coverage route mismatch: {row}")
        if row.get("contextFlowMatrixRoute") != "/qa/context-flow-matrix":
            raise AssertionError(f"{label} {name} context flow route mismatch: {row}")
        if not proofs:
            raise AssertionError(f"{label} {name} has no proof owners: {row}")
        if not routes:
            raise AssertionError(f"{label} {name} has no route owners: {row}")
        assert_file_proofs_exist(proofs, f"{label} {name}")
        for route in routes:
            if route not in coverage.get("routes", []) and route != "/qa/context-flow-matrix":
                raise AssertionError(f"{label} {name} names route outside evidence/context coverage: {row}")
        if row.get("proofOwnerExists") is not True:
            raise AssertionError(f"{label} {name} proof owner parity failed: {row}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-result-parser-fixture")
        if seeded.get("ok") is not True:
            raise AssertionError(f"result parser fixture seed failed: {seeded}")

        state = request("GET", "/state")
        matrix = request("GET", "/qa/evidence-lifecycle-flow-matrix")
        coverage = request("GET", "/qa/evidence-lifecycle-coverage")
        context_flow = request("GET", "/qa/context-flow-matrix")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"evidence lifecycle flow matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"evidence lifecycle flow matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"evidence lifecycle flow matrix proof-file parity mismatch: {matrix}")
        if matrix.get("proofOwnerFileParity") is not True:
            raise AssertionError(f"evidence lifecycle flow matrix owner parity mismatch: {matrix}")

        if matrix.get("stageCount") != coverage.get("stageCount"):
            raise AssertionError(f"evidence lifecycle flow matrix stage count mismatch: {matrix}")
        if matrix.get("storageTargetCount") != coverage.get("storageTargetCount"):
            raise AssertionError(f"evidence lifecycle flow matrix storage count mismatch: {matrix}")
        if matrix.get("handoffCount") != coverage.get("handoffCount"):
            raise AssertionError(f"evidence lifecycle flow matrix handoff count mismatch: {matrix}")
        if matrix.get("contextRetrievalSourceCount") != context_flow.get("retrievalSourceCount"):
            raise AssertionError(f"evidence lifecycle flow matrix context retrieval count mismatch: {matrix}")
        if matrix.get("contextDeliveryModeCount") != context_flow.get("deliveryModeCount"):
            raise AssertionError(f"evidence lifecycle flow matrix context delivery count mismatch: {matrix}")

        assert_rows(matrix.get("stageRows") or [], "stage", coverage.get("stages") or [], coverage, "stage")
        assert_rows(matrix.get("storageRows") or [], "storageTarget", coverage.get("storageTargets") or [], coverage, "storage")
        assert_rows(matrix.get("handoffRows") or [], "handoff", coverage.get("handoffs") or [], coverage, "handoff")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/evidence-lifecycle-flow-matrix" not in state_routes:
            raise AssertionError(f"state routes missing evidence lifecycle flow matrix: {state_routes}")

        chat_context = (index.get("groups") or {}).get("chatAndContext") or {}
        if chat_context.get("evidenceLifecycleFlowMatrixStageCount") != matrix.get("stageCount"):
            raise AssertionError(f"coverage index evidence lifecycle matrix stage count mismatch: {index}")
        if chat_context.get("evidenceLifecycleFlowMatrixStorageTargetCount") != matrix.get("storageTargetCount"):
            raise AssertionError(f"coverage index evidence lifecycle matrix storage count mismatch: {index}")
        if chat_context.get("evidenceLifecycleFlowMatrixHandoffCount") != matrix.get("handoffCount"):
            raise AssertionError(f"coverage index evidence lifecycle matrix handoff count mismatch: {index}")
        if chat_context.get("evidenceLifecycleFlowMatrixProofOwnerFileParity") != matrix.get("proofOwnerFileParity"):
            raise AssertionError(f"coverage index evidence lifecycle matrix owner parity mismatch: {index}")
        if chat_context.get("evidenceLifecycleFlowMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index evidence lifecycle matrix proof parity mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/evidence-lifecycle-flow-matrix",
            "evidence-lifecycle-flow-matrix-proof.py",
            "evidenceLifecycleFlowMatrixStageCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing evidence lifecycle flow matrix token {token}")

        print("evidence-lifecycle-flow-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"evidence-lifecycle-flow-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
