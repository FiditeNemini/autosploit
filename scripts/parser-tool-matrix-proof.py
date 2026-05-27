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
    "parser-tool-matrix-proof.py",
    "result-parser-routing-proof.py",
    "tool-execution-matrix-proof.py",
    "tool-family-fanout-coverage-proof.py",
    "coverage-index-proof.py",
    "app-qa-matrix-smoke-proof.py",
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

        seeded = request("POST", "/qa/seed-result-parser-fixture")
        if seeded.get("ok") is not True:
            raise AssertionError(f"result parser fixture seed failed: {seeded}")

        state = request("GET", "/state")
        matrix = request("GET", "/qa/parser-tool-matrix")
        result_parser = request("GET", "/qa/result-parser-coverage")
        tool_execution = request("GET", "/qa/tool-execution-matrix")
        coverage_index = request("GET", "/qa/coverage-index")

        tools_group = (coverage_index.get("groups") or {}).get("toolsAndParsers") or {}
        expected_structured = tools_group.get("resultParserStructuredTools") or []
        expected_raw_only = tools_group.get("resultParserRawOnlyTools") or []
        expected_tools = expected_structured + expected_raw_only

        if matrix.get("ok") is not True:
            raise AssertionError(f"parser tool matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"parser tool matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"parser tool matrix proof parity mismatch: {matrix}")
        if matrix.get("toolCount") != len(expected_tools):
            raise AssertionError(f"parser tool matrix count mismatch: {matrix}")
        if matrix.get("structuredToolCount") != len(expected_structured):
            raise AssertionError(f"parser tool matrix structured count mismatch: {matrix}")
        if matrix.get("rawOnlyToolCount") != len(expected_raw_only):
            raise AssertionError(f"parser tool matrix raw-only count mismatch: {matrix}")
        if matrix.get("parsedParity") is not True:
            raise AssertionError(f"parser tool matrix parsed parity mismatch: {matrix}")
        if matrix.get("toolExecutionParity") is not True:
            raise AssertionError(f"parser tool matrix execution parity mismatch: {matrix}")
        if matrix.get("resultParserRoute") != "/qa/result-parser-coverage":
            raise AssertionError(f"parser tool matrix result-parser route mismatch: {matrix}")
        if matrix.get("toolExecutionMatrixRoute") != "/qa/tool-execution-matrix":
            raise AssertionError(f"parser tool matrix execution route mismatch: {matrix}")
        if matrix.get("toolFamilyFanoutRoute") != "/qa/tool-family-fanout-coverage":
            raise AssertionError(f"parser tool matrix fanout route mismatch: {matrix}")

        rows = matrix.get("parserRows") or []
        if [row.get("tool") for row in rows] != expected_tools:
            raise AssertionError(f"parser tool matrix row order mismatch: {matrix}")
        tool_execution_names = {row.get("name") for row in (tool_execution.get("tools") or [])}
        parsed_structured = set(result_parser.get("parsedTools") or [])
        parsed_raw_only = set(result_parser.get("rawOnlyTools") or [])
        fanout_tools = set((tools_group.get("familyFanoutTools") or {}).values())
        for row in rows:
            tool = row.get("tool")
            proofs = row.get("proofs") or []
            assert_file_proofs_exist(proofs, tool or "parser row")
            if row.get("resultParserRoute") != "/qa/result-parser-coverage":
                raise AssertionError(f"parser row result route mismatch: {row}")
            if row.get("toolExecutionMatrixRoute") != "/qa/tool-execution-matrix":
                raise AssertionError(f"parser row execution route mismatch: {row}")
            if row.get("toolFamilyFanoutRoute") != "/qa/tool-family-fanout-coverage":
                raise AssertionError(f"parser row fanout route mismatch: {row}")
            if row.get("coverageIndexRoute") != "/qa/coverage-index":
                raise AssertionError(f"parser row coverage route mismatch: {row}")
            if row.get("toolExecutionKnown") != (tool in tool_execution_names):
                raise AssertionError(f"parser row execution known mismatch: {row}")
            if row.get("familyFanoutTool") != (tool in fanout_tools):
                raise AssertionError(f"parser row family fanout mismatch: {row}")
            if row.get("parserMode") == "structured":
                if row.get("parsed") != (tool in parsed_structured):
                    raise AssertionError(f"parser row structured parsed mismatch: {row}")
            elif row.get("parserMode") == "rawOnly":
                if row.get("parsed") != (tool in parsed_raw_only):
                    raise AssertionError(f"parser row raw-only parsed mismatch: {row}")
            else:
                raise AssertionError(f"parser row mode mismatch: {row}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/parser-tool-matrix" not in state_routes:
            raise AssertionError(f"state routes missing parser tool matrix: {state_routes}")

        if tools_group.get("parserToolMatrixCount") != matrix.get("toolCount"):
            raise AssertionError(f"coverage index parser tool matrix count mismatch: {coverage_index}")
        if tools_group.get("parserToolMatrixParsedParity") != matrix.get("parsedParity"):
            raise AssertionError(f"coverage index parser tool matrix parsed parity mismatch: {coverage_index}")
        if tools_group.get("parserToolMatrixToolExecutionParity") != matrix.get("toolExecutionParity"):
            raise AssertionError(f"coverage index parser tool matrix execution parity mismatch: {coverage_index}")
        if tools_group.get("parserToolMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index parser tool matrix proof parity mismatch: {coverage_index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/parser-tool-matrix",
            "parser-tool-matrix-proof.py",
            "parserToolMatrixCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing parser tool matrix token {token}")

        print("parser-tool-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"parser-tool-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
