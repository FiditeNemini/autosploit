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

EXPECTED_ROWS = [
    "boundedAutomaticContext",
    "onDemandContextSearch",
    "onDemandCVERetrieval",
    "stashRetrievalOnDemand",
    "tabRankedToolSchemaCap",
    "fullAgentSchemaSeparation",
    "shellDestructivePatternPolicy",
    "streamingDeltaIsolation",
    "responsesSessionReuse",
]

EXPECTED_CONTRACTS = {
    "automaticContextCap",
    "configuredContextLimitBounded",
    "contextSearchOnDemandTool",
    "cveSearchOnDemandTool",
    "lookupCVEOnDemandTool",
    "stashRetrievalOnDemand",
    "toolSchemaCap",
    "alwaysVisibleCallbackTools",
    "fullAgentSchemaSeparate",
    "shellRunVisible",
    "destructiveShellPolicy",
    "streamingContentDelta",
    "streamingReasoningDelta",
    "streamingToolCallDelta",
    "responsesPreviousResponseReuse",
    "coverageIndexMirror",
    "deepRuntimeMirror",
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


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        payload = request("GET", "/qa/context-prompt-injection-boundary")
        if payload.get("ok") is not True:
            raise AssertionError(f"context prompt-injection boundary route failed: {payload}")
        if payload.get("route") != "/qa/context-prompt-injection-boundary":
            raise AssertionError(f"context prompt-injection route label mismatch: {payload}")
        if payload.get("proofLevel") != "app-state-and-source-backed":
            raise AssertionError(f"context prompt-injection proof level mismatch: {payload}")
        if payload.get("boundaryMode") != "bounded-context-and-on-demand-tools":
            raise AssertionError(f"context prompt-injection boundary mode mismatch: {payload}")
        if payload.get("promptInjectionPolicy") != "search-on-demand-not-force-injected":
            raise AssertionError(f"context prompt-injection policy mismatch: {payload}")
        if payload.get("rows") != EXPECTED_ROWS:
            raise AssertionError(f"context prompt-injection row order mismatch: {payload}")
        if payload.get("rowCount") != len(EXPECTED_ROWS):
            raise AssertionError(f"context prompt-injection row count mismatch: {payload}")
        if payload.get("automaticInjectedContextCap") != 4:
            raise AssertionError(f"context prompt-injection context cap mismatch: {payload}")
        if not 1 <= payload.get("currentInjectedContextLimit", 0) <= 4:
            raise AssertionError(f"context prompt-injection current context limit not bounded: {payload}")
        if payload.get("toolSchemaCap") != 12:
            raise AssertionError(f"context prompt-injection tool schema cap mismatch: {payload}")
        if payload.get("toolSchemaPolicy") != "prompt-tab-ranked-installed-cap":
            raise AssertionError(f"context prompt-injection tool schema policy mismatch: {payload}")
        if payload.get("agentFullSchemaMode") != "separate-full-registry-for-agent-loop-not-per-turn-prompt":
            raise AssertionError(f"context prompt-injection agent schema mode mismatch: {payload}")
        if payload.get("cveRetrievalMode") != "on-demand-search-context-and-semantic-cve":
            raise AssertionError(f"context prompt-injection CVE retrieval mode mismatch: {payload}")
        if payload.get("stashRetrievalMode") != "on-demand-search_context-stash-note":
            raise AssertionError(f"context prompt-injection stash retrieval mode mismatch: {payload}")

        callback_tools = set(payload.get("callbackTools") or [])
        for name in ("search_context", "search_cve", "lookup_cve", "create_finding", "generate_report", "export_report"):
            if name not in callback_tools:
                raise AssertionError(f"context prompt-injection callback tool missing {name}: {payload}")
        always_visible = set(payload.get("alwaysVisibleTools") or [])
        for name in ("search_context", "search_cve", "lookup_cve", "create_finding", "generate_report", "export_report", "run_shell"):
            if name not in always_visible:
                raise AssertionError(f"context prompt-injection always-visible tool missing {name}: {payload}")

        shell_policy = payload.get("shellSafetyPolicy") or {}
        if shell_policy.get("tool") != "run_shell":
            raise AssertionError(f"context prompt-injection shell policy tool mismatch: {payload}")
        if shell_policy.get("availability") != "alwaysVisible":
            raise AssertionError(f"context prompt-injection shell policy availability mismatch: {payload}")
        if shell_policy.get("mode") != "allowWithDestructivePatternBlocklist":
            raise AssertionError(f"context prompt-injection shell policy mode mismatch: {payload}")
        if shell_policy.get("blockedPatternCount", 0) < 10:
            raise AssertionError(f"context prompt-injection shell blocklist too small: {payload}")
        if shell_policy.get("safeSampleAllowed") is not True or shell_policy.get("dangerSampleBlocked") is not True:
            raise AssertionError(f"context prompt-injection shell policy sample mismatch: {payload}")

        streaming = set(payload.get("streamingDeltaSurfaces") or [])
        for surface in ("delta.content", "delta.reasoning_content", "delta.tool_calls"):
            if surface not in streaming:
                raise AssertionError(f"context prompt-injection streaming surface missing {surface}: {payload}")

        contracts = payload.get("contracts") or {}
        missing_contracts = sorted(name for name in EXPECTED_CONTRACTS if contracts.get(name) is not True)
        if missing_contracts:
            raise AssertionError(f"context prompt-injection missing contracts {missing_contracts}: {payload}")
        if payload.get("contractCount") != len(EXPECTED_CONTRACTS):
            raise AssertionError(f"context prompt-injection contract count mismatch: {payload}")
        if payload.get("contractParity") is not True:
            raise AssertionError(f"context prompt-injection contract parity mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"context prompt-injection proof-file parity mismatch: {payload}")
        if payload.get("sourceFileParity") is not True:
            raise AssertionError(f"context prompt-injection source-file parity mismatch: {payload}")

        state = request("GET", "/state")
        routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/context-prompt-injection-boundary" not in routes:
            raise AssertionError(f"state route list missing prompt-injection boundary route: {routes}")

        deep = request("GET", "/qa/deep-runtime-flow-coverage")
        if "/qa/context-prompt-injection-boundary" not in (deep.get("routes") or []):
            raise AssertionError(f"deep runtime flow missing prompt-injection boundary route: {deep}")
        if deep.get("contextPromptInjectionBoundaryContractParity") is not True:
            raise AssertionError(f"deep runtime flow missing prompt-injection boundary parity: {deep}")

        index = request("GET", "/qa/coverage-index", timeout=120.0)
        chat_group = (index.get("groups") or {}).get("chatAndContext") or {}
        if "/qa/context-prompt-injection-boundary" not in (chat_group.get("endpoints") or []):
            raise AssertionError(f"coverage index chat group missing prompt-injection boundary route: {chat_group}")
        if chat_group.get("contextPromptInjectionBoundaryContractParity") is not True:
            raise AssertionError(f"coverage index missing prompt-injection boundary parity: {chat_group}")

        print("context-prompt-injection-boundary proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"context-prompt-injection-boundary proof failed: {exc}", flush=True)
        raise SystemExit(1)
