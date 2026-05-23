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

REQUIRED_CONTRACTS = {
    "boundedCatalog",
    "requestAudit",
    "resultToContext",
    "agentSearchContext",
    "embeddingAudit",
    "stashRetrieval",
    "newContextCachePreservation",
}

REQUIRED_ROUTES = {
    "/context/new",
    "/qa/context-packet",
    "/qa/seed-context",
    "/qa/seed-context-scope",
    "/qa/seed-catalog-embeddings",
    "/qa/seed-stash-retrieval",
    "/qa/seed-semantic-cves",
}

REQUIRED_PROOFS = {
    "context-catalog-proof.py",
    "result-context-catalog-proof.py",
    "agent-search-context-proof.py",
    "catalog-embedding-audit-proof.py",
    "stash-retrieval-proof.py",
    "semantic-cve-proof.py",
    "tool-fanout-status-proof.py",
    "request-audit-proof.py",
    "context-window-cache-proof.py",
    "persistence-proof.py",
}

REQUIRED_STATE_KEYS = {
    "contextCatalog",
    "requestContext",
    "contextWindow",
    "catalogEmbeddings",
    "stashRetrieval",
    "cveSemantic",
    "messages.contextSelections",
    "messages.toolSchemas",
}

REQUIRED_RETRIEVAL_SOURCES = [
    "asset.port",
    "finding",
    "tool.output",
    "stash.note",
    "cve",
]

REQUIRED_RETRIEVAL_SOURCE_PROOFS = {
    "asset.port": ["context-catalog-proof.py", "result-context-catalog-proof.py"],
    "finding": ["context-catalog-proof.py"],
    "tool.output": ["result-context-catalog-proof.py", "tool-fanout-status-proof.py"],
    "stash.note": ["context-catalog-proof.py", "stash-retrieval-proof.py"],
    "cve": ["semantic-cve-proof.py", "agent-search-context-proof.py"],
}

REQUIRED_DELIVERY_MODES = [
    "automaticBoundedInjection",
    "onDemandSearchContext",
    "persistedTurnAudit",
    "durableEmbeddingIndex",
    "activeScopeStashRetrieval",
]

REQUIRED_DELIVERY_MODE_PROOFS = {
    "automaticBoundedInjection": ["context-catalog-proof.py", "request-audit-proof.py"],
    "onDemandSearchContext": ["agent-search-context-proof.py"],
    "persistedTurnAudit": ["request-audit-proof.py", "persistence-proof.py"],
    "durableEmbeddingIndex": ["catalog-embedding-audit-proof.py"],
    "activeScopeStashRetrieval": ["stash-retrieval-proof.py"],
}


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


def assert_context_coverage() -> None:
    state = request("GET", "/state")
    coverage = request("GET", "/qa/context-coverage")

    if coverage.get("ok") is not True:
        raise AssertionError(f"/qa/context-coverage failed: {coverage}")

    contracts = coverage.get("contracts") or {}
    missing_contracts = sorted(name for name in REQUIRED_CONTRACTS if contracts.get(name) is not True)
    if missing_contracts:
        raise AssertionError(f"context coverage missing contracts {missing_contracts}: {coverage}")

    routes = set(coverage.get("routes") or [])
    missing_routes = sorted(REQUIRED_ROUTES.difference(routes))
    if missing_routes:
        raise AssertionError(f"context coverage missing routes {missing_routes}: {coverage}")

    proofs = set(coverage.get("proofs") or [])
    missing_proofs = sorted(REQUIRED_PROOFS.difference(proofs))
    if missing_proofs:
        raise AssertionError(f"context coverage missing proofs {missing_proofs}: {coverage}")
    if coverage.get("proofCount", 0) < len(REQUIRED_PROOFS):
        raise AssertionError(f"context coverage proof count mismatch: {coverage}")
    missing_files = sorted(name for name in REQUIRED_PROOFS if not (ROOT / "scripts" / name).is_file())
    if missing_files:
        raise AssertionError(f"context coverage names non-existent proof files: {missing_files}")
    if coverage.get("proofFileParity") is not True:
        raise AssertionError(f"context coverage proof file parity mismatch: {coverage}")

    if coverage.get("maxSnippetsDefault") != 4:
        raise AssertionError(f"context coverage should expose bounded default snippets: {coverage}")
    if coverage.get("searchToolName") != "search_context":
        raise AssertionError(f"context coverage should expose search_context tool name: {coverage}")
    if coverage.get("automaticInjectedContextCap") != 4:
        raise AssertionError(f"context coverage should expose automatic context cap: {coverage}")
    if not 1 <= coverage.get("currentInjectedContextLimit", 0) <= 4:
        raise AssertionError(f"context coverage should expose bounded current context limit: {coverage}")
    if coverage.get("retrievalSources") != REQUIRED_RETRIEVAL_SOURCES:
        raise AssertionError(f"context coverage retrieval sources mismatch: {coverage}")
    if coverage.get("retrievalSourceCount") != len(REQUIRED_RETRIEVAL_SOURCES):
        raise AssertionError(f"context coverage retrieval source count mismatch: {coverage}")
    if coverage.get("retrievalSourceParity") is not True:
        raise AssertionError(f"context coverage retrieval source parity mismatch: {coverage}")
    if coverage.get("retrievalSourceProofs") != REQUIRED_RETRIEVAL_SOURCE_PROOFS:
        raise AssertionError(f"context coverage retrieval source proof map mismatch: {coverage}")
    if coverage.get("retrievalSourceProofCount") != len(REQUIRED_RETRIEVAL_SOURCE_PROOFS):
        raise AssertionError(f"context coverage retrieval source proof count mismatch: {coverage}")
    if coverage.get("retrievalSourceProofParity") is not True:
        raise AssertionError(f"context coverage retrieval source proof parity mismatch: {coverage}")
    for source, proof_names in REQUIRED_RETRIEVAL_SOURCE_PROOFS.items():
        missing_source_files = sorted(name for name in proof_names if not (ROOT / "scripts" / name).is_file())
        if missing_source_files:
            raise AssertionError(f"context retrieval source {source} names missing proof files {missing_source_files}: {coverage}")
    if coverage.get("retrievalSourceProofFileParity") is not True:
        raise AssertionError(f"context retrieval source proof-file parity mismatch: {coverage}")
    if coverage.get("contextDeliveryModes") != REQUIRED_DELIVERY_MODES:
        raise AssertionError(f"context coverage delivery modes mismatch: {coverage}")
    if coverage.get("contextDeliveryModeCount") != len(REQUIRED_DELIVERY_MODES):
        raise AssertionError(f"context coverage delivery mode count mismatch: {coverage}")
    if coverage.get("contextDeliveryModeParity") is not True:
        raise AssertionError(f"context coverage delivery mode parity mismatch: {coverage}")
    if coverage.get("contextDeliveryModeProofs") != REQUIRED_DELIVERY_MODE_PROOFS:
        raise AssertionError(f"context coverage delivery mode proof map mismatch: {coverage}")
    if coverage.get("contextDeliveryModeProofCount") != len(REQUIRED_DELIVERY_MODE_PROOFS):
        raise AssertionError(f"context coverage delivery mode proof count mismatch: {coverage}")
    if coverage.get("contextDeliveryModeProofParity") is not True:
        raise AssertionError(f"context coverage delivery mode proof parity mismatch: {coverage}")
    for mode, proof_names in REQUIRED_DELIVERY_MODE_PROOFS.items():
        missing_mode_files = sorted(name for name in proof_names if not (ROOT / "scripts" / name).is_file())
        if missing_mode_files:
            raise AssertionError(f"context delivery mode {mode} names missing proof files {missing_mode_files}: {coverage}")
    if coverage.get("contextDeliveryModeProofFileParity") is not True:
        raise AssertionError(f"context delivery mode proof-file parity mismatch: {coverage}")
    state_keys = set(coverage.get("stateKeys") or [])
    missing_state_keys = sorted(REQUIRED_STATE_KEYS.difference(state_keys))
    if missing_state_keys:
        raise AssertionError(f"context coverage missing state keys {missing_state_keys}: {coverage}")

    qa = state.get("qaCoverage") or {}
    if "/qa/context-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing context coverage route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_context_coverage()
        print("context-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"context-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
