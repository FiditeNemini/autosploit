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

EXPECTED_STAGES = [
    "toolOutputCaptured",
    "parsedResultStored",
    "findingDraftCreated",
    "findingPersisted",
    "stashNoteCreated",
    "reportSectionGenerated",
    "reportArtifactExported",
    "agentDraftQueued",
    "contextCatalogIndexed",
    "boundedContextSelected",
    "searchContextRetrieves",
]

EXPECTED_STORAGE_TARGETS = [
    "resultsStore.rawResults",
    "resultsStore.parsedAssets",
    "resultsStore.vulns",
    "findings",
    "stashItems",
    "generatedReport",
    "reportExport",
    "contextCatalog",
    "catalogEmbeddings",
    "requestContext",
    "activityFeed",
]

EXPECTED_HANDOFFS = [
    "toolOutputToParser",
    "parserToResultsTab",
    "parserToContextCatalog",
    "webVulnToFindingWizard",
    "findingWizardToFindingsStore",
    "findingToReportPreview",
    "findingToReportExport",
    "findingToAgentDraft",
    "findingToContextCatalog",
    "stashToContextCatalog",
    "stashToChatHandoff",
    "searchContextToAgentLoop",
]

EXPECTED_ROUTES = [
    "/qa/evidence-lifecycle-coverage",
    "/qa/seed-result-parser-fixture",
    "/qa/context-packet",
    "/qa/finding-wizard-submit",
    "/qa/report-generate-action",
    "/qa/report-export-action",
    "/qa/report-create-finding",
    "/qa/report-submit-finding",
    "/qa/stash-add",
    "/qa/stash-send",
    "/qa/result-parser-coverage",
    "/qa/context-coverage",
    "/qa/report-coverage",
    "/qa/stash-coverage",
]

EXPECTED_PROOFS = [
    "evidence-lifecycle-coverage-proof.py",
    "result-parser-routing-proof.py",
    "result-context-catalog-proof.py",
    "context-catalog-proof.py",
    "stash-retrieval-proof.py",
    "stash-actions-proof.py",
    "stash-send-chat-control-proof.py",
    "web-direct-actions-proof.py",
    "finding-wizard-submit-proof.py",
    "report-generate-action-proof.py",
    "report-export-proof.py",
    "report-agent-action-proof.py",
]

EXPECTED_CONTEXT_POLICY = {
    "automaticInjection": "bounded",
    "automaticSnippetCap": 4,
    "targetedRetrieval": "search_context",
    "forceInjectAllEvidence": False,
    "persistTurnAudit": True,
}


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


def assert_payload(payload: dict) -> None:
    if payload.get("ok") is not True:
        raise AssertionError(f"evidence lifecycle coverage route failed: {payload}")
    if payload.get("stages") != EXPECTED_STAGES:
        raise AssertionError(f"evidence lifecycle stage list mismatch: {payload}")
    if payload.get("stageCount") != len(EXPECTED_STAGES):
        raise AssertionError(f"evidence lifecycle stage count mismatch: {payload}")
    if payload.get("stageParity") is not True:
        raise AssertionError(f"evidence lifecycle stage parity mismatch: {payload}")

    if payload.get("storageTargets") != EXPECTED_STORAGE_TARGETS:
        raise AssertionError(f"evidence lifecycle storage targets mismatch: {payload}")
    if payload.get("storageTargetCount") != len(EXPECTED_STORAGE_TARGETS):
        raise AssertionError(f"evidence lifecycle storage target count mismatch: {payload}")
    if payload.get("storageTargetParity") is not True:
        raise AssertionError(f"evidence lifecycle storage target parity mismatch: {payload}")

    if payload.get("handoffs") != EXPECTED_HANDOFFS:
        raise AssertionError(f"evidence lifecycle handoff list mismatch: {payload}")
    if payload.get("handoffCount") != len(EXPECTED_HANDOFFS):
        raise AssertionError(f"evidence lifecycle handoff count mismatch: {payload}")
    if payload.get("handoffParity") is not True:
        raise AssertionError(f"evidence lifecycle handoff parity mismatch: {payload}")

    if payload.get("routes") != EXPECTED_ROUTES:
        raise AssertionError(f"evidence lifecycle route list mismatch: {payload}")
    if payload.get("routeCount") != len(EXPECTED_ROUTES):
        raise AssertionError(f"evidence lifecycle route count mismatch: {payload}")
    if payload.get("routeParity") is not True:
        raise AssertionError(f"evidence lifecycle route parity mismatch: {payload}")

    if payload.get("proofs") != EXPECTED_PROOFS:
        raise AssertionError(f"evidence lifecycle proof list mismatch: {payload}")
    if payload.get("proofCount") != len(EXPECTED_PROOFS):
        raise AssertionError(f"evidence lifecycle proof count mismatch: {payload}")
    if payload.get("proofFileParity") is not True:
        raise AssertionError(f"evidence lifecycle proof-file parity mismatch: {payload}")
    missing_files = sorted(name for name in EXPECTED_PROOFS if not (ROOT / "scripts" / name).is_file())
    if missing_files:
        raise AssertionError(f"evidence lifecycle names non-existent proof files: {missing_files}")

    if payload.get("contextPolicy") != EXPECTED_CONTEXT_POLICY:
        raise AssertionError(f"evidence lifecycle context policy mismatch: {payload}")
    if payload.get("contextPolicyParity") is not True:
        raise AssertionError(f"evidence lifecycle context policy parity mismatch: {payload}")


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

        payload = request("GET", "/qa/evidence-lifecycle-coverage")
        assert_payload(payload)

        index = request("GET", "/qa/coverage-index")
        chat_context = (index.get("groups") or {}).get("chatAndContext") or {}
        if chat_context.get("evidenceLifecycleStages") != payload.get("stages"):
            raise AssertionError(f"coverage index evidence lifecycle stages mismatch: {index}")
        if chat_context.get("evidenceLifecycleHandoffs") != payload.get("handoffs"):
            raise AssertionError(f"coverage index evidence lifecycle handoffs mismatch: {index}")
        if chat_context.get("evidenceLifecycleProofFileParity") != payload.get("proofFileParity"):
            raise AssertionError(f"coverage index evidence lifecycle proof parity mismatch: {index}")

        state = request("GET", "/state")
        if "/qa/evidence-lifecycle-coverage" not in ((state.get("qaCoverage") or {}).get("stateRoutes") or []):
            raise AssertionError(f"state route list missing evidence lifecycle route: {state.get('qaCoverage')}")

        print("evidence-lifecycle-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"evidence-lifecycle-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
