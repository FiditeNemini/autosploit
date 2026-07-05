#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
ROUTE = "/qa/per-turn-runtime-contract"
PROOF = "per-turn-runtime-contract-proof.py"

EXPECTED_ROWS = [
    "turnInput",
    "contextBudget",
    "contextCompaction",
    "cveImportSelection",
    "semanticCVERetrieval",
    "stashMemoryRetrieval",
    "promptInjectionBoundary",
    "toolSchemaSelection",
    "liveToolProgressStatus",
    "engineRequestBudget",
    "responsesReuse",
    "streamingDeltaHandling",
    "reasoningToolParser",
    "parallelSessionBatching",
    "l2DiskCache",
    "turboQuantKVCache",
    "hybridSSMAsyncReDerive",
    "resultLogAndGapBoundary",
]

REQUIRED_STATUS_SURFACES = {
    "chatInput",
    "contextInspector",
    "cveSettings",
    "stashPanel",
    "toolButton",
    "activityFeed",
    "engineRequest",
    "streamingMessage",
    "reasoningBlock",
    "agentStatusLine",
    "cacheStats",
    "gapLedger",
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


def seed_cve_semantic_state(marker: Path) -> None:
    seeded = request("POST", "/qa/seed-cve-settings-status")
    if seeded.get("ok") is not True:
        raise AssertionError(f"CVE settings seed failed: {seeded}")
    imported = request("POST", "/qa/cve-settings-action", json.dumps({
        "action": "importList",
        "source": "CVE-2021-41773\nCVE-2021-42013\nCVE-2022-22965",
        "includeOnly": "CVE-2021-41773,CVE-2022-22965",
    }))
    if imported.get("ok") is not True:
        raise AssertionError(f"CVE import-list action failed: {imported}")
    semantic_seed = request("POST", "/qa/seed-semantic-cves")
    if semantic_seed.get("ok") is not True:
        raise AssertionError(f"semantic CVE seed failed: {semantic_seed}")
    packet = request("POST", "/qa/context-packet", json.dumps({
        "query": "semantic vector lane should find the matching record",
        "maxSnippets": 5,
        "includeAssets": False,
        "includeFindings": False,
        "includeRecentToolOutput": False,
        "includeStash": False,
        "cveMode": "semantic",
    }))["packet"]
    if "CVE-QA-SEMANTIC-HIT" not in packet:
        raise AssertionError(f"semantic context packet missing hit:\n{packet}")
    if not marker.exists():
        raise AssertionError("fake CVE embedder was not invoked")


def run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        marker = Path(tmp) / "embedder-called.jsonl"
        embedder = Path(tmp) / "fake-cve-embedder.py"
        embedder.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import json
                import sys
                from pathlib import Path

                Path({str(marker)!r}).write_text(json.dumps({{"argv": sys.argv}}) + "\\n", encoding="utf-8")
                print(json.dumps({{"vector": [1.0, 0.0, 0.0, 0.0], "dimensions": 4}}))
                """
            ),
            encoding="utf-8",
        )
        embedder.chmod(0o755)

        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["EXPLOITBOT_CVE_EMBEDDER_PATH"] = str(embedder)
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

        try:
            if app.wait(timeout=30) != 0:
                raise RuntimeError("build_and_run --verify failed")
            wait_for_app()
            seed_cve_semantic_state(marker)

            contract = request("GET", ROUTE, timeout=45.0)
            state = request("GET", "/state")
            index = request("GET", "/qa/coverage-index", timeout=120.0)

            if contract.get("ok") is not True:
                raise AssertionError(f"per-turn runtime contract failed: {contract}")
            if contract.get("route") != ROUTE:
                raise AssertionError(f"per-turn runtime contract route mismatch: {contract}")
            if contract.get("proofLevel") != "per-turn-status-surface-and-live-artifact-backed":
                raise AssertionError(f"per-turn runtime contract proof level mismatch: {contract}")
            if contract.get("rowIds") != EXPECTED_ROWS:
                raise AssertionError(f"per-turn runtime contract row order mismatch: {contract}")
            if contract.get("rowCount") != len(EXPECTED_ROWS):
                raise AssertionError(f"per-turn runtime contract row count mismatch: {contract}")
            if contract.get("readyRowCount") != len(EXPECTED_ROWS):
                raise AssertionError(f"per-turn runtime contract ready row count mismatch: {contract}")
            if contract.get("contractParity") is not True:
                raise AssertionError(f"per-turn runtime contract parity mismatch: {contract}")
            if contract.get("proofFileParity") is not True:
                raise AssertionError(f"per-turn runtime contract proof parity mismatch: {contract}")
            if PROOF not in (contract.get("proofs") or []):
                raise AssertionError(f"per-turn runtime contract missing owner proof: {contract}")
            if contract.get("objectiveComplete") is not False:
                raise AssertionError(f"per-turn runtime contract should preserve incomplete objective state: {contract}")

            surfaces = set(contract.get("statusSurfaces") or [])
            if not REQUIRED_STATUS_SURFACES.issubset(surfaces):
                raise AssertionError(f"per-turn runtime contract missing status surfaces: {contract}")

            rows = {row.get("id"): row for row in contract.get("rows") or []}
            for row_id in EXPECTED_ROWS:
                row = rows.get(row_id) or {}
                if row.get("status") != "ready":
                    raise AssertionError(f"per-turn row not ready {row_id}: {row}")
                if row.get("contractOK") is not True:
                    raise AssertionError(f"per-turn row contract failed {row_id}: {row}")
                if row.get("proofFileParity") is not True:
                    raise AssertionError(f"per-turn row proof parity failed {row_id}: {row}")
                if not row.get("inputContract"):
                    raise AssertionError(f"per-turn row missing input contract {row_id}: {row}")
                if not row.get("statusSurface"):
                    raise AssertionError(f"per-turn row missing status surface {row_id}: {row}")
                if not row.get("evidence"):
                    raise AssertionError(f"per-turn row missing evidence {row_id}: {row}")
                if not row.get("routes"):
                    raise AssertionError(f"per-turn row missing routes {row_id}: {row}")
                if not row.get("proofs"):
                    raise AssertionError(f"per-turn row missing proofs {row_id}: {row}")

            if rows["contextBudget"].get("maxTokens", 0) <= 0:
                raise AssertionError(f"context budget row missing max tokens: {rows['contextBudget']}")
            if rows["contextCompaction"].get("compactionFormat") != "single-line-snippet":
                raise AssertionError(f"context compaction row mismatch: {rows['contextCompaction']}")
            if rows["cveImportSelection"].get("includeOnlyMode") != "includeOnly-cve-id-allowlist":
                raise AssertionError(f"CVE include-list row mismatch: {rows['cveImportSelection']}")
            if rows["promptInjectionBoundary"].get("schemaCap", 0) > 12:
                raise AssertionError(f"tool schema cap too high: {rows['promptInjectionBoundary']}")
            if rows["responsesReuse"].get("reuseMode") != "store-response-session-and-resolve-previous-response-id":
                raise AssertionError(f"Responses reuse row mismatch: {rows['responsesReuse']}")
            required_deltas = {"delta.content", "delta.reasoning_content", "delta.tool_calls"}
            if not required_deltas.issubset(set(rows["streamingDeltaHandling"].get("deltaSurfaces") or [])):
                raise AssertionError(f"streaming delta row mismatch: {rows['streamingDeltaHandling']}")
            if rows["parallelSessionBatching"].get("qwenMaxRunningObserved", 0) < 4:
                raise AssertionError(f"parallel/batching row missing Qwen 4-way evidence: {rows['parallelSessionBatching']}")
            if rows["l2DiskCache"].get("diskHits", 0) < 1:
                raise AssertionError(f"L2 disk cache row missing hit evidence: {rows['l2DiskCache']}")
            if rows["turboQuantKVCache"].get("qwenKVBits") != 4:
                raise AssertionError(f"TurboQuant row missing q4 evidence: {rows['turboQuantKVCache']}")
            if rows["hybridSSMAsyncReDerive"].get("completed", 0) < 1:
                raise AssertionError(f"SSM async rederive row missing completion: {rows['hybridSSMAsyncReDerive']}")
            if rows["resultLogAndGapBoundary"].get("knownGapCount", 0) < 1:
                raise AssertionError(f"gap boundary row should preserve known gaps: {rows['resultLogAndGapBoundary']}")

            state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
            if ROUTE not in state_routes:
                raise AssertionError(f"state route list missing {ROUTE}: {state_routes}")

            release_group = (index.get("groups") or {}).get("releaseReadiness") or {}
            if ROUTE not in (release_group.get("endpoints") or []):
                raise AssertionError(f"coverage index release group missing {ROUTE}: {release_group}")
            if release_group.get("perTurnRuntimeContractRowCount") != len(EXPECTED_ROWS):
                raise AssertionError(f"coverage index per-turn row count mismatch: {release_group}")
            if release_group.get("perTurnRuntimeContractParity") is not True:
                raise AssertionError(f"coverage index per-turn parity mismatch: {release_group}")
            if release_group.get("perTurnRuntimeContractProofFileParity") is not True:
                raise AssertionError(f"coverage index per-turn proof parity mismatch: {release_group}")
            print("per-turn-runtime-contract proof passed")
        finally:
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if app.poll() is None:
                app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"per-turn-runtime-contract proof failed: {exc}", flush=True)
        raise SystemExit(1)
