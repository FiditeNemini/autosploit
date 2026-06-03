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
    "context-flow-matrix-proof.py",
    "context-coverage-proof.py",
    "agent-flow-inventory-proof.py",
    "agent-loop-phase-matrix-proof.py",
    "coverage-index-proof.py",
    "app-qa-matrix-smoke-proof.py",
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


def assert_file_proofs_exist(proofs: list[str], label: str) -> None:
    missing = [proof for proof in proofs if not (ROOT / "scripts" / proof).is_file()]
    if missing:
        raise AssertionError(f"{label} names missing proof files: {missing}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        state = request("GET", "/state")
        matrix = request("GET", "/qa/context-flow-matrix")
        context = request("GET", "/qa/context-coverage")
        agent_flow = request("GET", "/qa/agent-flow-inventory")
        phase_matrix = request("GET", "/qa/agent-loop-phase-matrix")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"context flow matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"context flow matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"context flow matrix proof-file parity mismatch: {matrix}")
        if matrix.get("retrievalSourceCount") != context.get("retrievalSourceCount"):
            raise AssertionError(f"context flow matrix retrieval source count mismatch: {matrix}")
        if matrix.get("deliveryModeCount") != context.get("contextDeliveryModeCount"):
            raise AssertionError(f"context flow matrix delivery mode count mismatch: {matrix}")
        if matrix.get("retrievalSourceParity") is not True:
            raise AssertionError(f"context flow matrix retrieval source parity mismatch: {matrix}")
        if matrix.get("deliveryModeParity") is not True:
            raise AssertionError(f"context flow matrix delivery mode parity mismatch: {matrix}")
        if matrix.get("proofOwnerFileParity") is not True:
            raise AssertionError(f"context flow matrix proof owner parity mismatch: {matrix}")
        if matrix.get("agentFlowPhaseCoverageParity") != agent_flow.get("phaseCoverageParity"):
            raise AssertionError(f"context flow matrix agent-flow phase parity mismatch: {matrix}")
        if matrix.get("agentLoopContextPhase") != "retrieveDynamicContext":
            raise AssertionError(f"context flow matrix agent loop phase mismatch: {matrix}")

        retrieval_rows = matrix.get("retrievalRows") or []
        delivery_rows = matrix.get("deliveryRows") or []
        if [row.get("source") for row in retrieval_rows] != context.get("retrievalSources"):
            raise AssertionError(f"context flow matrix retrieval row order mismatch: {matrix}")
        if [row.get("mode") for row in delivery_rows] != context.get("contextDeliveryModes"):
            raise AssertionError(f"context flow matrix delivery row order mismatch: {matrix}")
        for row in retrieval_rows:
            proofs = row.get("proofs") or []
            if proofs != (context.get("retrievalSourceProofs") or {}).get(row.get("source")):
                raise AssertionError(f"{row.get('source')} retrieval proof mismatch: {row}")
            assert_file_proofs_exist(proofs, row.get("source") or "retrieval")
            if row.get("contextRoute") != "/qa/context-coverage":
                raise AssertionError(f"{row.get('source')} retrieval route mismatch: {row}")
            if row.get("agentFlowSourcePhase") != "contextCatalogue":
                raise AssertionError(f"{row.get('source')} retrieval agent source phase mismatch: {row}")
        for row in delivery_rows:
            proofs = row.get("proofs") or []
            if proofs != (context.get("contextDeliveryModeProofs") or {}).get(row.get("mode")):
                raise AssertionError(f"{row.get('mode')} delivery proof mismatch: {row}")
            assert_file_proofs_exist(proofs, row.get("mode") or "delivery")
            if row.get("contextRoute") != "/qa/context-coverage":
                raise AssertionError(f"{row.get('mode')} delivery route mismatch: {row}")
            if row.get("agentLoopPhase") != "retrieveDynamicContext":
                raise AssertionError(f"{row.get('mode')} delivery agent loop phase mismatch: {row}")

        phase_rows = {row.get("phase"): row for row in phase_matrix.get("phaseRows") or []}
        if "contextCatalogue" not in (phase_rows.get("retrieveDynamicContext") or {}).get("sourcePhases", []):
            raise AssertionError(f"agent loop phase matrix missing context source phase: {phase_matrix}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/context-flow-matrix" not in state_routes:
            raise AssertionError(f"state routes missing context flow matrix: {state_routes}")

        chat_context = (index.get("groups") or {}).get("chatAndContext") or {}
        if chat_context.get("contextFlowMatrixRetrievalSourceCount") != matrix.get("retrievalSourceCount"):
            raise AssertionError(f"coverage index context flow retrieval count mismatch: {index}")
        if chat_context.get("contextFlowMatrixDeliveryModeCount") != matrix.get("deliveryModeCount"):
            raise AssertionError(f"coverage index context flow delivery count mismatch: {index}")
        if chat_context.get("contextFlowMatrixProofOwnerFileParity") != matrix.get("proofOwnerFileParity"):
            raise AssertionError(f"coverage index context flow owner parity mismatch: {index}")
        if chat_context.get("contextFlowMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index context flow proof parity mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in ["/qa/context-flow-matrix", "context-flow-matrix-proof.py", "contextFlowMatrixRetrievalSourceCount"]:
            if token not in docs_text:
                raise AssertionError(f"docs missing context flow matrix token {token}")

        print("context-flow-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"context-flow-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
