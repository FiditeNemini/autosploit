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

EXPECTED_EXECUTION_STATES = ["suggested", "pendingApproval", "running", "complete", "failed", "canceled"]
EXPECTED_SOURCE_HOOKS = {
    "callback": ["ChatService.callbackDispatch", "AppState.callbackWiring"],
    "subprocess": ["ToolDefinitions.buildCliArgs", "ToolExecutor.execute"],
}
EXPECTED_PROOFS = [
    "tool-execution-matrix-proof.py",
    "tool-registry-coverage-proof.py",
    "tool-flow-coverage-proof.py",
    "agent-tool-authorization-proof.py",
    "tool-fanout-status-proof.py",
    "result-parser-routing-proof.py",
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
        matrix = request("GET", "/qa/tool-execution-matrix")
        registry = request("GET", "/qa/tool-coverage")
        tool_flow = request("GET", "/qa/tool-flow-coverage")
        auth = request("GET", "/qa/agent-tool-authorization-coverage")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"tool execution matrix route failed: {matrix}")
        if matrix.get("toolCount") != registry.get("toolCount"):
            raise AssertionError(f"tool execution matrix count mismatch: {matrix}")
        if matrix.get("rowParity") is not True:
            raise AssertionError(f"tool execution matrix row parity mismatch: {matrix}")
        if matrix.get("executionStateParity") is not True:
            raise AssertionError(f"tool execution state parity mismatch: {matrix}")
        if matrix.get("sourceHookParity") is not True:
            raise AssertionError(f"tool execution source hook parity mismatch: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"tool execution proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"tool execution proof-file parity mismatch: {matrix}")

        registry_by_name = {tool.get("name"): tool for tool in registry.get("tools") or []}
        rows = matrix.get("tools") or []
        if len(rows) != registry.get("toolCount"):
            raise AssertionError(f"tool execution row count mismatch: {matrix}")
        if set(row.get("name") for row in rows) != set(registry_by_name):
            raise AssertionError(f"tool execution row name set mismatch: {matrix}")

        auth_policies = auth.get("policies") or {}
        for row in rows:
            name = row.get("name")
            registry_row = registry_by_name.get(name) or {}
            if row.get("binary") != registry_row.get("binary"):
                raise AssertionError(f"{name} binary mismatch: {row}")
            if row.get("execution") != registry_row.get("execution"):
                raise AssertionError(f"{name} execution mismatch: {row}")
            if row.get("resultMode") != registry_row.get("resultMode"):
                raise AssertionError(f"{name} result mode mismatch: {row}")
            if row.get("tabs") != registry_row.get("tabs"):
                raise AssertionError(f"{name} tabs mismatch: {row}")
            if row.get("sourceHooks") != EXPECTED_SOURCE_HOOKS[row.get("execution")]:
                raise AssertionError(f"{name} source hook mismatch: {row}")
            if row.get("authorizationPolicies") != auth_policies:
                raise AssertionError(f"{name} authorization policies mismatch: {row}")
            if row.get("executionStates") != EXPECTED_EXECUTION_STATES:
                raise AssertionError(f"{name} execution states mismatch: {row}")
            if row.get("agentLoopRoute") != "/qa/agent-loop-coverage":
                raise AssertionError(f"{name} missing agent loop route: {row}")
            if row.get("toolFlowRoute") != "/qa/tool-flow-coverage":
                raise AssertionError(f"{name} missing tool flow route: {row}")

        if matrix.get("executionCounts") != registry.get("executionCounts"):
            raise AssertionError(f"tool execution count map mismatch: {matrix}")
        if matrix.get("resultModeCounts") != registry.get("resultModeCounts"):
            raise AssertionError(f"tool execution result mode count map mismatch: {matrix}")
        if matrix.get("toolFlowProofCount") != tool_flow.get("proofCount"):
            raise AssertionError(f"tool execution tool-flow proof count mismatch: {matrix}")
        if matrix.get("authorizationPolicyCount") != auth.get("policyCount"):
            raise AssertionError(f"tool execution auth policy count mismatch: {matrix}")

        qa_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/tool-execution-matrix" not in qa_routes:
            raise AssertionError(f"state routes missing tool execution matrix: {qa_routes}")

        tools_group = (index.get("groups") or {}).get("toolsAndParsers") or {}
        if tools_group.get("toolExecutionMatrixCount") != matrix.get("toolCount"):
            raise AssertionError(f"coverage index tool execution count mismatch: {index}")
        if tools_group.get("toolExecutionMatrixParity") != matrix.get("rowParity"):
            raise AssertionError(f"coverage index tool execution parity mismatch: {index}")
        if tools_group.get("toolExecutionMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index tool execution proof parity mismatch: {index}")
        if tools_group.get("toolExecutionMatrixAuthorizationPolicyCount") != matrix.get("authorizationPolicyCount"):
            raise AssertionError(f"coverage index tool execution auth count mismatch: {index}")
        if tools_group.get("toolExecutionMatrixExecutionStateCount") != matrix.get("executionStateCount"):
            raise AssertionError(f"coverage index tool execution state count mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in ["/qa/tool-execution-matrix", "tool-execution-matrix-proof.py", "toolExecutionMatrixCount"]:
            if token not in docs_text:
                raise AssertionError(f"docs missing tool execution token {token}")

        print("tool-execution-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"tool-execution-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
