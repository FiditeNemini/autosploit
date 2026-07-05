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
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-context-budget-compaction.json"

EXPECTED_POLICY_STEPS = [
    "selectBoundedContext",
    "applyHardContextPacketBudget",
    "compactCatalogSnippets",
    "applyMaxTokenBudget",
    "preserveCacheOnNewContext",
    "reuseStashAndCVEOnDemand",
]

EXPECTED_CONTRACTS = {
    "automaticContextCap",
    "configuredContextLimitBounded",
    "maxTokensForwarded",
    "maxIterationsBounded",
    "compactCatalogFormatting",
    "contextPacketHardBudget",
    "promptInjectionBoundedContext",
    "newContextPreservesEngineCache",
    "stashContextOnDemand",
    "cveContextOnDemand",
    "cacheSessionBadges",
}

EXPECTED_PROOFS = {
    "context-budget-compaction-proof.py",
    "context-packet-budget-proof.py",
    "context-coverage-proof.py",
    "context-flow-matrix-proof.py",
    "context-window-cache-proof.py",
    "chat-coverage-proof.py",
    "stash-retrieval-proof.py",
    "semantic-cve-proof.py",
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
            request("GET", "/messages", timeout=2.0)
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"app test server did not become ready: {last_error}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    output = Path(os.environ.get("EXPLOITBOT_CONTEXT_BUDGET_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    report = {
        "ok": False,
        "proofType": "context-budget-compaction",
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "appApi": APP_API,
    }
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        state = request("GET", "/state")
        budget = request("GET", "/qa/context-budget-compaction")
        context = request("GET", "/qa/context-coverage")
        chat = request("GET", "/qa/chat-coverage")
        index = request("GET", "/qa/coverage-index", timeout=120.0)
        report["stateEngineConfig"] = state.get("engineConfig")
        report["stateChat"] = state.get("chat")
        report["budget"] = budget
        report["context"] = context
        report["chat"] = chat
        report["coverageChatAndContext"] = (index.get("groups") or {}).get("chatAndContext")

        if budget.get("ok") is not True:
            raise AssertionError(f"context budget route failed: {budget}")
        if budget.get("policySteps") != EXPECTED_POLICY_STEPS:
            raise AssertionError(f"context budget policy step mismatch: {budget}")
        if budget.get("policyStepCount") != len(EXPECTED_POLICY_STEPS):
            raise AssertionError(f"context budget policy step count mismatch: {budget}")
        if budget.get("automaticInjectedContextCap") != 4:
            raise AssertionError(f"context budget cap mismatch: {budget}")
        if not 1 <= budget.get("currentInjectedContextLimit", 0) <= 4:
            raise AssertionError(f"context budget current limit is not bounded: {budget}")
        if budget.get("configuredMaxSnippets", 0) < budget.get("currentInjectedContextLimit", 0):
            raise AssertionError(f"context budget configured snippets below current limit: {budget}")
        if budget.get("maxTokens") != (state.get("engineConfig") or {}).get("maxTokens"):
            raise AssertionError(f"context budget max tokens not tied to engine config: {budget}")
        if budget.get("chatMaxTokens") != budget.get("maxTokens"):
            raise AssertionError(f"context budget chat max tokens not tied to chat service: {budget}")
        if budget.get("maxIterations") != (state.get("chat") or {}).get("maxIterations"):
            raise AssertionError(f"context budget max iterations not tied to chat service: {budget}")
        if budget.get("contextPacketMaxCharacters") != 6000:
            raise AssertionError(f"context packet max character budget mismatch: {budget}")
        if budget.get("contextPacketMaxSelectedSnippets") != 8:
            raise AssertionError(f"context packet selected snippet budget mismatch: {budget}")
        if budget.get("cacheResponseMethod") != "prefix-cache-l2-turboquant":
            raise AssertionError(f"context budget cache response method mismatch: {budget}")
        if budget.get("newContextBehavior") != "clear-visible-chat-preserve-engine-cache-session":
            raise AssertionError(f"context budget new-context behavior mismatch: {budget}")
        if budget.get("compactionFormat") != "single-line-snippet":
            raise AssertionError(f"context budget compaction format mismatch: {budget}")
        if budget.get("promptInjectionPolicy") != "search-on-demand-not-force-injected":
            raise AssertionError(f"context budget prompt-injection policy mismatch: {budget}")
        if budget.get("retrievalSources") != context.get("retrievalSources"):
            raise AssertionError(f"context budget retrieval source mismatch: {budget}")
        if budget.get("contextDeliveryModes") != context.get("contextDeliveryModes"):
            raise AssertionError(f"context budget delivery mode mismatch: {budget}")
        if budget.get("cacheSessionFields") != chat.get("cacheSessionFields"):
            raise AssertionError(f"context budget cache session field mismatch: {budget}")

        contracts = budget.get("contracts") or {}
        missing_contracts = sorted(name for name in EXPECTED_CONTRACTS if contracts.get(name) is not True)
        if missing_contracts:
            raise AssertionError(f"context budget missing contracts {missing_contracts}: {budget}")

        proofs = set(budget.get("proofs") or [])
        missing_proofs = sorted(EXPECTED_PROOFS.difference(proofs))
        if missing_proofs:
            raise AssertionError(f"context budget missing proofs {missing_proofs}: {budget}")
        if budget.get("proofFileParity") is not True:
            raise AssertionError(f"context budget proof-file parity mismatch: {budget}")

        routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/context-budget-compaction" not in routes:
            raise AssertionError(f"state route list missing context budget route: {routes}")

        group = (index.get("groups") or {}).get("chatAndContext") or {}
        if group.get("contextBudgetPolicySteps") != EXPECTED_POLICY_STEPS:
            raise AssertionError(f"coverage index missing context budget policy steps: {group}")
        if group.get("contextBudgetContractParity") is not True:
            raise AssertionError(f"coverage index context budget contract parity mismatch: {group}")
        if group.get("contextBudgetProofFileParity") is not True:
            raise AssertionError(f"coverage index context budget proof parity mismatch: {group}")

        report["ok"] = True
        report["status"] = {
            "policySteps": "PASS",
            "maxTokensForwarded": "PASS",
            "maxIterationsBounded": "PASS",
            "contextPacketBudget": "PASS",
            "cachePreservingNewContext": "PASS",
            "coverageIndexParity": "PASS",
        }
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"context-budget-compaction proof passed; wrote {output}")
    except Exception as exc:
        report["error"] = str(exc)
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        raise
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"context-budget-compaction proof failed: {exc}", flush=True)
        raise SystemExit(1)
