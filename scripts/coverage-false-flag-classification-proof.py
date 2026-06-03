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
ROUTE = "/qa/coverage-false-flag-classification"
PROOF = "coverage-false-flag-classification-proof.py"

REQUIRED_BUCKETS = {
    "known-gap",
    "fixture-required",
    "intentional-negative-policy",
    "distribution-held",
    "not-required",
    "bundled-runtime-info",
    "historical-artifact",
    "unsupported-multimodal-inventory",
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


def false_flags(payload: object, prefix: tuple[str, ...] = ()) -> list[str]:
    flags: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            flags.extend(false_flags(value, prefix + (str(key),)))
    elif payload is False:
        flags.append(".".join(prefix))
    return flags


def assert_payload(route_payload: dict, index_payload: dict) -> None:
    if route_payload.get("route") != ROUTE:
        raise AssertionError(f"route label mismatch: {route_payload}")
    if route_payload.get("ok") is not True:
        raise AssertionError(f"false flag classification route failed: {route_payload}")
    if route_payload.get("classificationParity") is not True:
        raise AssertionError(f"false flag classification parity failed: {route_payload}")
    if route_payload.get("proofFileParity") is not True:
        raise AssertionError(f"false flag classification proof parity failed: {route_payload}")
    if PROOF not in (route_payload.get("proofs") or []):
        raise AssertionError(f"false flag classification proof missing from route: {route_payload}")

    expected = sorted(false_flags(index_payload.get("groups") or {}))
    actual = sorted(route_payload.get("sourceFalseFlags") or [])
    if actual != expected:
        raise AssertionError(
            "source false flag list mismatch:\n"
            f"expected={json.dumps(expected, indent=2)}\n"
            f"actual={json.dumps(actual, indent=2)}"
        )
    if route_payload.get("falseFlagCount") != len(expected):
        raise AssertionError(f"false flag count mismatch: {route_payload}")
    if route_payload.get("classifiedFalseFlagCount") != len(expected):
        raise AssertionError(f"classified false flag count mismatch: {route_payload}")
    if route_payload.get("unclassifiedFalseFlags") != []:
        raise AssertionError(f"unclassified false flags remain: {route_payload}")

    rows = route_payload.get("classifications") or []
    by_path = {row.get("path"): row for row in rows}
    if sorted(by_path) != expected:
        raise AssertionError(f"classification rows do not match source flags: {route_payload}")

    buckets = set(route_payload.get("classificationBuckets") or [])
    missing_buckets = sorted(REQUIRED_BUCKETS - buckets)
    if missing_buckets:
        raise AssertionError(f"missing classification buckets {missing_buckets}: {route_payload}")
    if route_payload.get("classificationBucketCount") != len(buckets):
        raise AssertionError(f"classification bucket count mismatch: {route_payload}")

    for path, row in by_path.items():
        bucket = row.get("bucket")
        if bucket not in REQUIRED_BUCKETS:
            raise AssertionError(f"unexpected bucket for {path}: {row}")
        if not row.get("reason"):
            raise AssertionError(f"classification row missing reason for {path}: {row}")
        if not row.get("evidenceRoutes"):
            raise AssertionError(f"classification row missing evidence routes for {path}: {row}")
        if not row.get("evidenceProofs"):
            raise AssertionError(f"classification row missing evidence proofs for {path}: {row}")

    expected_examples = {
        "releaseReadiness.betaDistributionReady": "distribution-held",
        "releaseReadiness.notaryProfileRequired": "not-required",
        "releaseReadiness.pythonEngineVenv": "bundled-runtime-info",
        "chatAndContext.cveImportEmbeddingContracts.semanticEmbeddingState": "fixture-required",
        "toolsAndParsers.parserToolMatrixParsedParity": "fixture-required",
        "chatAndContext.evidenceLifecycleContextPolicy.forceInjectAllEvidence": "intentional-negative-policy",
        "appState.qwenMultimodalPromotionReady": "known-gap",
        "appState.auditUnsupportedMultimodalBlocked": "unsupported-multimodal-inventory",
        "appState.artifactLedgerLiveProofStatus.docs/live-proofs/checkpoint-485-qwen-mxfp-live-current.json": "historical-artifact",
        "tabsAndSessions.agentToolAuthorizationPolicies.manual.executesWithoutApproval": "intentional-negative-policy",
    }
    for path, bucket in expected_examples.items():
        row = by_path.get(path)
        if not row:
            raise AssertionError(f"expected classified example missing {path}: {route_payload}")
        if row.get("bucket") != bucket:
            raise AssertionError(f"expected {path} bucket {bucket}, got {row}")

    expected_routes = {
        "/qa/coverage-index",
        "/qa/state-dependent-contract-matrix",
        "/qa/gap-ledger",
        "/qa/artifact-ledger",
        "/qa/audit-ledger",
        "/qa/release-readiness",
        "/qa/beta-readiness-coverage",
        "/qa/objective-runtime-coverage",
        "/qa/agent-tool-authorization-coverage",
    }
    if not expected_routes.issubset(set(route_payload.get("evidenceRoutes") or [])):
        raise AssertionError(f"route evidence set incomplete: {route_payload}")

    state = request("GET", "/state")
    state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
    if ROUTE not in state_routes:
        raise AssertionError(f"state route list missing {ROUTE}: {state_routes}")

    index_group = ((request("GET", "/qa/coverage-index").get("groups") or {}).get("appState") or {})
    if ROUTE not in (index_group.get("endpoints") or []):
        raise AssertionError(f"coverage index appState group missing {ROUTE}: {index_group}")
    if PROOF not in (index_group.get("proofs") or []):
        raise AssertionError(f"coverage index appState group missing {PROOF}: {index_group}")
    if index_group.get("falseFlagClassificationParity") is not True:
        raise AssertionError(f"coverage index false flag parity mirror failed: {index_group}")
    if index_group.get("unclassifiedFalseFlagCount") != 0:
        raise AssertionError(f"coverage index should mirror zero unclassified flags: {index_group}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        index_payload = request("GET", "/qa/coverage-index")
        route_payload = request("GET", ROUTE)
        assert_payload(route_payload, index_payload)
        print("coverage-false-flag-classification proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"coverage-false-flag-classification proof failed: {exc}", flush=True)
        raise SystemExit(1)
