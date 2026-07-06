#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
ROUTE = "/qa/objective-flow-execution-graph"
PROOF = "objective-flow-execution-graph-proof.py"

EXPECTED_NODES = [
    "sessionStart",
    "contextBudget",
    "contextCompaction",
    "cveImportInclude",
    "semanticCVERetrieval",
    "stashRetrieval",
    "promptInjectionBoundary",
    "toolSchemaSelection",
    "responsesReuse",
    "streamingDeltas",
    "reasoningAndToolParser",
    "parallelAgentSessions",
    "continuousBatching",
    "l2DiskCache",
    "turboQuantKV",
    "hybridSSMReDerive",
    "betaReadiness",
    "knownGapBoundary",
]

EXPECTED_EDGES = [
    ("sessionStart", "contextBudget"),
    ("contextBudget", "contextCompaction"),
    ("contextCompaction", "cveImportInclude"),
    ("cveImportInclude", "semanticCVERetrieval"),
    ("semanticCVERetrieval", "stashRetrieval"),
    ("stashRetrieval", "promptInjectionBoundary"),
    ("promptInjectionBoundary", "toolSchemaSelection"),
    ("toolSchemaSelection", "responsesReuse"),
    ("responsesReuse", "streamingDeltas"),
    ("streamingDeltas", "reasoningAndToolParser"),
    ("reasoningAndToolParser", "parallelAgentSessions"),
    ("parallelAgentSessions", "continuousBatching"),
    ("continuousBatching", "l2DiskCache"),
    ("l2DiskCache", "turboQuantKV"),
    ("turboQuantKV", "hybridSSMReDerive"),
    ("hybridSSMReDerive", "betaReadiness"),
    ("betaReadiness", "knownGapBoundary"),
]

REQUIRED_NODE_ROUTES = {
    "contextBudget": "/qa/context-budget-compaction",
    "cveImportInclude": "/qa/cve-import-embedding-coverage",
    "semanticCVERetrieval": "/qa/cve-import-embedding-coverage",
    "stashRetrieval": "/qa/context-coverage",
    "promptInjectionBoundary": "/qa/context-prompt-injection-boundary",
    "responsesReuse": "/qa/streaming-parser-reuse",
    "streamingDeltas": "/qa/streaming-parser-reuse",
    "parallelAgentSessions": "/qa/session-context-cache-flow",
    "continuousBatching": "/qa/continuous-batching-coverage",
    "l2DiskCache": "/qa/cache-artifact-matrix",
    "turboQuantKV": "/qa/cache-artifact-matrix",
    "hybridSSMReDerive": "/qa/continuous-batching-coverage",
    "knownGapBoundary": "/qa/gap-ledger",
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


def assert_graph(graph: dict) -> None:
    if graph.get("ok") is not True:
        raise AssertionError(f"objective execution graph failed: {graph}")
    if graph.get("route") != ROUTE:
        raise AssertionError(f"objective execution graph route label mismatch: {graph}")
    if graph.get("proofLevel") != "ordered-objective-flow-route-proof-and-live-artifact-backed":
        raise AssertionError(f"objective execution graph proof level mismatch: {graph}")
    if graph.get("nodeIds") != EXPECTED_NODES:
        raise AssertionError(f"objective execution graph node order mismatch: {graph}")
    if graph.get("nodeCount") != len(EXPECTED_NODES):
        raise AssertionError(f"objective execution graph node count mismatch: {graph}")
    if graph.get("edgeCount") != len(EXPECTED_EDGES):
        raise AssertionError(f"objective execution graph edge count mismatch: {graph}")
    if graph.get("graphParity") is not True:
        raise AssertionError(f"objective execution graph parity failed: {graph}")
    if graph.get("proofFileParity") is not True:
        raise AssertionError(f"objective execution graph proof parity failed: {graph}")
    if PROOF not in (graph.get("proofs") or []):
        raise AssertionError(f"objective execution graph missing owner proof: {graph}")
    if graph.get("blockedNodeCount") != 0:
        raise AssertionError(f"objective execution graph should have no blocked nodes: {graph}")
    if graph.get("knownGapNodeIds") != ["knownGapBoundary"]:
        raise AssertionError(f"objective execution graph known-gap node mismatch: {graph}")
    if graph.get("objectiveComplete") is not False:
        raise AssertionError(f"objective execution graph should preserve incomplete objective state: {graph}")

    edges = [(edge.get("from"), edge.get("to")) for edge in graph.get("edges") or []]
    if edges != EXPECTED_EDGES:
        raise AssertionError(f"objective execution graph edge order mismatch: {graph}")

    rows = {row.get("id"): row for row in graph.get("nodes") or []}
    for node_id in EXPECTED_NODES:
        row = rows.get(node_id)
        if not row:
            raise AssertionError(f"objective execution graph missing node {node_id}: {graph}")
        if row.get("status") not in {"ready", "tracked-known-gap"}:
            raise AssertionError(f"objective execution graph bad node status {node_id}: {row}")
        if not row.get("objectiveRows"):
            raise AssertionError(f"objective execution graph node missing objective rows {node_id}: {row}")
        if not row.get("proofs"):
            raise AssertionError(f"objective execution graph node missing proofs {node_id}: {row}")
        if row.get("proofFileParity") is not True:
            raise AssertionError(f"objective execution graph node proof parity failed {node_id}: {row}")
        route = REQUIRED_NODE_ROUTES.get(node_id)
        if route and route not in (row.get("routes") or []):
            raise AssertionError(f"objective execution graph node {node_id} missing route {route}: {row}")

    stream = rows["streamingDeltas"]
    required_events = {
        "response.output_text.delta",
        "response.reasoning.delta",
        "response.function_call_arguments.delta",
        "response.completed",
    }
    if not required_events.issubset(set(stream.get("streamingEvents") or [])):
        raise AssertionError(f"streaming node missing required events: {stream}")

    parser = rows["reasoningAndToolParser"]
    if parser.get("reasoningDelta") is not True or parser.get("toolParserDelta") is not True:
        raise AssertionError(f"reasoning/tool parser node missing delta contracts: {parser}")

    for cache_node in ("l2DiskCache", "turboQuantKV", "hybridSSMReDerive"):
        row = rows[cache_node]
        if not row.get("liveArtifacts"):
            raise AssertionError(f"cache node {cache_node} missing live artifacts: {row}")
        if row.get("liveArtifactParity") is not True:
            raise AssertionError(f"cache node {cache_node} live artifact parity failed: {row}")

    state = request("GET", "/state")
    state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
    if ROUTE not in state_routes:
        raise AssertionError(f"state route list missing {ROUTE}: {state_routes}")

    index = request("GET", "/qa/coverage-index", timeout=120.0)
    release_group = (index.get("groups") or {}).get("releaseReadiness") or {}
    if ROUTE not in (release_group.get("endpoints") or []):
        raise AssertionError(f"coverage index release group missing {ROUTE}: {release_group}")
    if release_group.get("objectiveFlowExecutionNodeCount") != len(EXPECTED_NODES):
        raise AssertionError(f"coverage index execution graph node count mismatch: {release_group}")
    if release_group.get("objectiveFlowExecutionGraphParity") is not True:
        raise AssertionError(f"coverage index execution graph parity mismatch: {release_group}")
    if release_group.get("objectiveFlowExecutionProofFileParity") is not True:
        raise AssertionError(f"coverage index execution graph proof parity mismatch: {release_group}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        graph = request("GET", ROUTE, timeout=45.0)
        assert_graph(graph)
        print("objective-flow-execution-graph proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"objective-flow-execution-graph proof failed: {exc}", flush=True)
        raise SystemExit(1)
