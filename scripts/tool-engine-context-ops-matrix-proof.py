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

EXPECTED_ROWS = [
    "toolRegistryExecution",
    "liveToolProgressTelemetry",
    "engineParserCacheDefaults",
    "responsesStreamingReasoningTools",
    "promptInjectionBoundary",
    "cveImportSemanticEmbeddings",
    "contextSessionEfficiency",
    "stashMemoryRetrieval",
    "parallelAgentsContinuousBatching",
    "l2TurboQuantHybridSSMCache",
    "localQwenMiniMaxRuntimeLane",
    "coverageIndexMirrors",
]

REQUIRED_PROOFS = {
    "tool-engine-context-ops-matrix-proof.py",
    "tool-flow-coverage-proof.py",
    "tool-execution-matrix-proof.py",
    "agent-live-tool-status-proof.py",
    "runtime-coverage-proof.py",
    "streaming-parser-reuse-proof.py",
    "context-prompt-injection-boundary-proof.py",
    "cve-import-embedding-coverage-proof.py",
    "context-session-efficiency-matrix-proof.py",
    "session-context-cache-flow-proof.py",
    "cache-artifact-matrix-proof.py",
    "runtime-local-model-lane-proof.py",
}


def request(method: str, path: str, body: dict | str | None = None, timeout: float = 45.0):
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


def seed_cve_embedding_state(embedder: Path, marker: Path) -> None:
    seeded = request("POST", "/qa/seed-cve-settings-status")
    if seeded.get("ok") is not True:
        raise AssertionError(f"CVE settings seed failed: {seeded}")
    imported = request("POST", "/qa/cve-settings-action", {
        "action": "importList",
        "source": "CVE-2021-41773\nCVE-2021-42013\nCVE-2022-22965",
        "includeOnly": "CVE-2021-41773,CVE-2022-22965",
    })
    if imported.get("ok") is not True:
        raise AssertionError(f"CVE import-list action failed: {imported}")
    semantic_seed = request("POST", "/qa/seed-semantic-cves")
    if semantic_seed.get("ok") is not True:
        raise AssertionError(f"semantic CVE seed failed: {semantic_seed}")
    packet = request("POST", "/qa/context-packet", {
        "query": "semantic vector lane should find the matching record",
        "maxSnippets": 5,
        "includeAssets": False,
        "includeFindings": False,
        "includeRecentToolOutput": False,
        "includeStash": False,
        "cveMode": "semantic",
    })["packet"]
    if "CVE-QA-SEMANTIC-HIT" not in packet:
        raise AssertionError(f"semantic context packet missing hit:\n{packet}")
    if not marker.exists():
        raise AssertionError(f"fake CVE embedder was not invoked: {embedder}")


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
            seed_cve_embedding_state(embedder, marker)

            matrix = request("GET", "/qa/tool-engine-context-ops-matrix")
            tool_flow = request("GET", "/qa/tool-flow-coverage")
            runtime = request("GET", "/qa/runtime-coverage")
            streaming = request("GET", "/qa/streaming-parser-reuse")
            boundary = request("GET", "/qa/context-prompt-injection-boundary")
            cve = request("GET", "/qa/cve-import-embedding-coverage")
            context_session = request("GET", "/qa/context-session-efficiency-matrix")
            cache = request("GET", "/qa/cache-artifact-matrix")
            lane = request("GET", "/qa/runtime-local-model-lane")
            index = request("GET", "/qa/coverage-index", timeout=120.0)
            state = request("GET", "/state")

            if matrix.get("ok") is not True:
                raise AssertionError(f"tool/engine/context ops matrix failed: {matrix}")
            if matrix.get("route") != "/qa/tool-engine-context-ops-matrix":
                raise AssertionError(f"tool/engine/context route label mismatch: {matrix}")
            if matrix.get("proofLevel") != "tool-engine-context-state-and-live-artifact-backed":
                raise AssertionError(f"tool/engine/context proof level mismatch: {matrix}")
            if matrix.get("rowIds") != EXPECTED_ROWS:
                raise AssertionError(f"tool/engine/context row order mismatch: {matrix}")
            if matrix.get("rowCount") != len(EXPECTED_ROWS):
                raise AssertionError(f"tool/engine/context row count mismatch: {matrix}")
            if matrix.get("readyRowCount") != len(EXPECTED_ROWS):
                raise AssertionError(f"tool/engine/context ready row count mismatch: {matrix}")
            if matrix.get("contractParity") is not True:
                raise AssertionError(f"tool/engine/context contract parity mismatch: {matrix}")
            if matrix.get("proofFileParity") is not True:
                raise AssertionError(f"tool/engine/context proof-file parity mismatch: {matrix}")

            rows = {row.get("id"): row for row in matrix.get("rows") or []}
            for row_id in EXPECTED_ROWS:
                row = rows.get(row_id) or {}
                if row.get("status") != "ready":
                    raise AssertionError(f"tool/engine/context row not ready {row_id}: {row}")
                if row.get("contractOK") is not True:
                    raise AssertionError(f"tool/engine/context row contract failed {row_id}: {row}")
                if row.get("proofFileParity") is not True:
                    raise AssertionError(f"tool/engine/context row proof parity failed {row_id}: {row}")
                if not row.get("route"):
                    raise AssertionError(f"tool/engine/context row missing route {row_id}: {row}")

            if rows["toolRegistryExecution"].get("toolCount") != tool_flow.get("toolCount"):
                raise AssertionError(f"tool registry row drifted: {rows['toolRegistryExecution']}")
            if rows["toolRegistryExecution"].get("toolSchemaCap") != 8:
                raise AssertionError(f"tool schema cap missing: {rows['toolRegistryExecution']}")
            if rows["liveToolProgressTelemetry"].get("statusCount") != tool_flow.get("tabActivityStatusCount"):
                raise AssertionError(f"tool status row drifted: {rows['liveToolProgressTelemetry']}")
            if rows["engineParserCacheDefaults"].get("runtimeContractParity") != runtime.get("ok"):
                raise AssertionError(f"engine/cache row drifted: {rows['engineParserCacheDefaults']}")
            if "turboQuantKV" not in rows["engineParserCacheDefaults"].get("cacheComponents", []):
                raise AssertionError(f"TurboQuant cache component missing: {rows['engineParserCacheDefaults']}")
            if rows["responsesStreamingReasoningTools"].get("responsesReuseMode") != streaming.get("responsesStoreSessionMode"):
                raise AssertionError(f"Responses row drifted: {rows['responsesStreamingReasoningTools']}")
            if rows["promptInjectionBoundary"].get("policy") != boundary.get("promptInjectionPolicy"):
                raise AssertionError(f"prompt-injection row drifted: {rows['promptInjectionBoundary']}")
            if rows["cveImportSemanticEmbeddings"].get("selectedImportIds") != ["CVE-2021-41773", "CVE-2022-22965"]:
                raise AssertionError(f"CVE import row selected IDs mismatch: {rows['cveImportSemanticEmbeddings']}")
            if rows["cveImportSemanticEmbeddings"].get("semanticUsedEmbedding") is not True:
                raise AssertionError(f"CVE embedding row missing semantic state: {rows['cveImportSemanticEmbeddings']}")
            if rows["contextSessionEfficiency"].get("rowCount") != context_session.get("rowCount"):
                raise AssertionError(f"context/session row drifted: {rows['contextSessionEfficiency']}")
            if rows["parallelAgentsContinuousBatching"].get("qwenMaxRunningObserved", 0) < 4:
                raise AssertionError(f"Qwen batching evidence missing: {rows['parallelAgentsContinuousBatching']}")
            if rows["parallelAgentsContinuousBatching"].get("minimaxMaxRunningObserved", 0) < 2:
                raise AssertionError(f"MiniMax batching evidence missing: {rows['parallelAgentsContinuousBatching']}")
            if rows["l2TurboQuantHybridSSMCache"].get("cacheArtifactContractParity") != cache.get("contractParity"):
                raise AssertionError(f"cache row drifted: {rows['l2TurboQuantHybridSSMCache']}")
            if rows["l2TurboQuantHybridSSMCache"].get("qwenKVBits") != 4:
                raise AssertionError(f"Qwen q4 KV missing: {rows['l2TurboQuantHybridSSMCache']}")
            if rows["localQwenMiniMaxRuntimeLane"].get("contractParity") != lane.get("contractParity"):
                raise AssertionError(f"local runtime lane row drifted: {rows['localQwenMiniMaxRuntimeLane']}")

            proofs = set(matrix.get("proofs") or [])
            missing_proofs = sorted(REQUIRED_PROOFS.difference(proofs))
            if missing_proofs:
                raise AssertionError(f"tool/engine/context matrix missing proofs {missing_proofs}: {matrix}")

            state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
            if "/qa/tool-engine-context-ops-matrix" not in state_routes:
                raise AssertionError(f"state route list missing tool/engine/context matrix: {state_routes}")

            groups = index.get("groups") or {}
            for group_name in ("toolsAndParsers", "runtimeAndCache", "chatAndContext"):
                group = groups.get(group_name) or {}
                if "/qa/tool-engine-context-ops-matrix" not in (group.get("endpoints") or []):
                    raise AssertionError(f"coverage index {group_name} missing matrix route: {group}")
                if "tool-engine-context-ops-matrix-proof.py" not in (group.get("proofs") or []):
                    raise AssertionError(f"coverage index {group_name} missing matrix proof: {group}")

            runtime_group = groups.get("runtimeAndCache") or {}
            if runtime_group.get("toolEngineContextOpsRowCount") != len(EXPECTED_ROWS):
                raise AssertionError(f"coverage index runtime group matrix row count mismatch: {runtime_group}")
            if runtime_group.get("toolEngineContextOpsContractParity") is not True:
                raise AssertionError(f"coverage index runtime group matrix contract parity mismatch: {runtime_group}")

            print("tool-engine-context-ops-matrix proof passed")
        finally:
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if app.poll() is None:
                app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"tool-engine-context-ops-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
