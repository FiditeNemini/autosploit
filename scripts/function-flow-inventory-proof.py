#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
SOURCE_ROOT = ROOT / "ExploitBot" / "Sources" / "ExploitBot"
APP_STATE = SOURCE_ROOT / "Models" / "AppState.swift"
DOCS = [
    ROOT / "docs" / "app-system-review-2026-05-21.md",
    ROOT / "docs" / "app-flow-inventory-2026-05-21.md",
]

EXPECTED_GROUPS = [
    "appStateActions",
    "qaAndProofs",
    "agentLoop",
    "chatAndContext",
    "runtimeAndModels",
    "settingsAndVisuals",
    "tabAndEvidence",
    "servicesAndExecution",
    "viewCallbacks",
    "support",
]

EXPECTED_PROOFS = [
    "function-flow-inventory-proof.py",
    "action-state-inventory-proof.py",
    "endpoint-inventory-proof.py",
    "view-inventory-proof.py",
    "service-inventory-proof.py",
    "agent-flow-inventory-proof.py",
    "coverage-index-proof.py",
    "app-qa-matrix-smoke-proof.py",
]


def swift_files() -> list[Path]:
    roots = [
        SOURCE_ROOT / "App",
        SOURCE_ROOT / "Models",
        SOURCE_ROOT / "Services",
        SOURCE_ROOT / "Views",
    ]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(sorted(root.rglob("*.swift")))
    return sorted(files)


def function_names(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^\s*(?:@[A-Za-z_][A-Za-z0-9_]*(?:\([^)]*\))?\s+)*"
        r"(?:(?:private|public|internal|fileprivate|static|class|mutating|nonisolated|override|final)\s+)*"
        r"func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        re.MULTILINE,
    )
    return pattern.findall(text)


def group_for(path: Path, name: str) -> str:
    rel = str(path.relative_to(SOURCE_ROOT))
    lowered = name.lower()
    if rel == "Models/AppState.swift":
        if name.startswith("record") or name.startswith("seed") or name.startswith("select") or name.startswith("copy") or name.startswith("delete") or name.startswith("save") or name.startswith("create") or name.startswith("switch"):
            return "appStateActions"
        if "snapshot" in lowered or "inventory" in lowered or "coverage" in lowered or "ledger" in lowered or "proof" in lowered or "qa" in lowered:
            return "qaAndProofs"
        if "agent" in lowered or "approval" in lowered or "autopilot" in lowered:
            return "agentLoop"
        if "chat" in lowered or "context" in lowered or "message" in lowered or "stash" in lowered:
            return "chatAndContext"
        if "engine" in lowered or "model" in lowered or "runtime" in lowered or "cache" in lowered:
            return "runtimeAndModels"
        if "settings" in lowered or "cve" in lowered or "inference" in lowered or "theme" in lowered:
            return "settingsAndVisuals"
        if "tab" in lowered or "result" in lowered or "finding" in lowered or "report" in lowered or "osint" in lowered:
            return "tabAndEvidence"
        return "support"
    if rel.startswith("Services/"):
        if "Agent" in rel or name.startswith("on"):
            return "agentLoop"
        if any(token in rel for token in ["Chat", "Context", "Finding", "Results", "Stash", "CVE"]):
            return "chatAndContext"
        if any(token in rel for token in ["Engine", "Model"]):
            return "runtimeAndModels"
        return "servicesAndExecution"
    if rel.startswith("Views/") or rel.startswith("App/"):
        return "viewCallbacks"
    return "support"


def proof_for(group: str) -> str:
    return {
        "appStateActions": "action-state-inventory-proof.py",
        "qaAndProofs": "endpoint-inventory-proof.py",
        "agentLoop": "agent-flow-inventory-proof.py",
        "chatAndContext": "context-coverage-proof.py",
        "runtimeAndModels": "runtime-coverage-proof.py",
        "settingsAndVisuals": "settings-coverage-proof.py",
        "tabAndEvidence": "tab-action-coverage-proof.py",
        "servicesAndExecution": "service-inventory-proof.py",
        "viewCallbacks": "view-inventory-proof.py",
        "support": "app-qa-matrix-smoke-proof.py",
    }[group]


def source_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in swift_files():
        rel = str(path.relative_to(ROOT))
        for name in function_names(path):
            group = group_for(path, name)
            rows.append(
                {
                    "file": rel,
                    "name": name,
                    "group": group,
                    "proofOwner": proof_for(group),
                }
            )
    return rows


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

        rows = source_rows()
        payload = request("GET", "/qa/function-flow-inventory")
        if payload.get("ok") is not True:
            raise AssertionError(f"function-flow inventory route failed: {payload}")
        if payload.get("sourceRoot") != "ExploitBot/Sources/ExploitBot":
            raise AssertionError(f"function-flow source root mismatch: {payload}")
        if payload.get("functions") != rows:
            raise AssertionError(f"function-flow function list mismatch: {payload}")
        if payload.get("functionCount") != len(rows):
            raise AssertionError(f"function-flow function count mismatch: {payload}")
        if payload.get("groups") != EXPECTED_GROUPS:
            raise AssertionError(f"function-flow groups mismatch: {payload}")
        expected_counts = dict(Counter(row["group"] for row in rows))
        expected_counts = {group: expected_counts.get(group, 0) for group in EXPECTED_GROUPS}
        if payload.get("groupCounts") != expected_counts:
            raise AssertionError(f"function-flow group count mismatch: {payload}")
        if payload.get("groupParity") is not True:
            raise AssertionError(f"function-flow group parity mismatch: {payload}")
        if any(not item.get("proofOwner") for item in payload.get("functions") or []):
            raise AssertionError(f"function-flow has functions without proof owners: {payload}")
        if payload.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"function-flow proofs mismatch: {payload}")
        if payload.get("proofCount") != len(EXPECTED_PROOFS):
            raise AssertionError(f"function-flow proof count mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"function-flow proof-file parity mismatch: {payload}")

        state = request("GET", "/state")
        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/function-flow-inventory" not in state_routes:
            raise AssertionError(f"state route list missing function-flow inventory route: {state_routes}")

        index = request("GET", "/qa/coverage-index")
        app_group = (index.get("groups") or {}).get("appState") or {}
        if app_group.get("functionFlowInventoryCount") != payload.get("functionCount"):
            raise AssertionError(f"coverage index function-flow count mismatch: {index}")
        if app_group.get("functionFlowInventoryGroupCounts") != payload.get("groupCounts"):
            raise AssertionError(f"coverage index function-flow groups mismatch: {index}")
        if app_group.get("functionFlowInventoryProofFileParity") != payload.get("proofFileParity"):
            raise AssertionError(f"coverage index function-flow parity mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in ["/qa/function-flow-inventory", "function-flow-inventory-proof.py", "functionFlowInventoryCount"]:
            if token not in docs_text:
                raise AssertionError(f"docs missing function-flow token {token}")

        print("function-flow-inventory proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"function-flow-inventory proof failed: {exc}", flush=True)
        raise SystemExit(1)
