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
SERVICE_ROOT = ROOT / "ExploitBot" / "Sources" / "ExploitBot" / "Services"

EXPECTED_GROUPS = [
    "agentAndChat",
    "contextAndEvidence",
    "runtimeAndModels",
    "toolsAndExecution",
    "persistenceAndReporting",
    "support",
]

EXPECTED_PROOFS = [
    "service-inventory-proof.py",
    "app-qa-matrix-smoke-proof.py",
    "coverage-index-proof.py",
    "tool-registry-coverage-proof.py",
    "tool-flow-coverage-proof.py",
    "context-coverage-proof.py",
    "runtime-coverage-proof.py",
    "agent-loop-coverage-proof.py",
    "persistence-proof.py",
    "report-generate-action-proof.py",
]


def service_files() -> list[Path]:
    return sorted(SERVICE_ROOT.rglob("*.swift"))


def group_for(file_name: str) -> str:
    if file_name in {"AgentManager.swift", "ChatService.swift", "ActivityFeed.swift"}:
        return "agentAndChat"
    if file_name in {"ContextCatalogService.swift", "CVEService.swift", "FindingService.swift", "ResultsStore.swift", "StashService.swift"}:
        return "contextAndEvidence"
    if file_name in {"EngineManager.swift", "ModelDownloader.swift", "ModelFolderInspector.swift"}:
        return "runtimeAndModels"
    if file_name in {"ToolDefinitions.swift", "ToolExecutor.swift", "ToolInstaller.swift", "ScopeChecker.swift"}:
        return "toolsAndExecution"
    if file_name in {"Database.swift", "ReportService.swift"}:
        return "persistenceAndReporting"
    return "support"


def proof_for(file_name: str) -> str:
    if file_name in {"AgentManager.swift", "ChatService.swift"}:
        return "agent-loop-coverage-proof.py"
    if file_name in {"ContextCatalogService.swift", "CVEService.swift", "FindingService.swift", "ResultsStore.swift", "StashService.swift"}:
        return "context-coverage-proof.py"
    if file_name in {"EngineManager.swift", "ModelDownloader.swift", "ModelFolderInspector.swift"}:
        return "runtime-coverage-proof.py"
    if file_name in {"ToolDefinitions.swift", "ToolExecutor.swift", "ToolInstaller.swift", "ScopeChecker.swift"}:
        return "tool-flow-coverage-proof.py"
    if file_name == "Database.swift":
        return "persistence-proof.py"
    if file_name == "ReportService.swift":
        return "report-generate-action-proof.py"
    return "app-qa-matrix-smoke-proof.py"


def type_names(text: str) -> list[str]:
    return re.findall(r"^(?:final\s+)?(?:class|struct|enum|actor)\s+(\w+)", text, re.MULTILINE)


def function_names(text: str) -> list[str]:
    return re.findall(
        r"^\s{4}(?:@\w+(?:\([^)]*\))?\s+)*(?:private\s+|public\s+|internal\s+|fileprivate\s+)*(?:static\s+|class\s+)?func\s+(\w+)\s*\(",
        text,
        re.MULTILINE,
    )


def source_services() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in service_files():
        text = path.read_text(encoding="utf-8")
        funcs = function_names(text)
        types = type_names(text)
        file_name = path.name
        rows.append(
            {
                "file": str(path.relative_to(ROOT)),
                "group": group_for(file_name),
                "proofOwner": proof_for(file_name),
                "types": types,
                "typeCount": len(types),
                "functions": funcs,
                "functionCount": len(funcs),
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

        services = source_services()
        payload = request("GET", "/qa/service-inventory")
        if payload.get("ok") is not True:
            raise AssertionError(f"service inventory route failed: {payload}")
        if payload.get("sourceRoot") != "ExploitBot/Sources/ExploitBot/Services":
            raise AssertionError(f"service inventory source root mismatch: {payload}")
        if payload.get("services") != services:
            raise AssertionError(f"service inventory list mismatch: {payload}")
        if payload.get("serviceFileCount") != len(services):
            raise AssertionError(f"service inventory file count mismatch: {payload}")
        if payload.get("typeCount") != sum(item["typeCount"] for item in services):
            raise AssertionError(f"service inventory type count mismatch: {payload}")
        if payload.get("functionCount") != sum(item["functionCount"] for item in services):
            raise AssertionError(f"service inventory function count mismatch: {payload}")
        if payload.get("functionCount", 0) < 150:
            raise AssertionError(f"service inventory function count too low: {payload}")
        if any(not item.get("proofOwner") for item in payload.get("services") or []):
            raise AssertionError(f"service inventory missing proof owner: {payload}")
        if any(not item.get("group") for item in payload.get("services") or []):
            raise AssertionError(f"service inventory missing group: {payload}")

        if payload.get("groups") != EXPECTED_GROUPS:
            raise AssertionError(f"service inventory group list mismatch: {payload}")
        group_counts = payload.get("groupCounts") or {}
        if set(group_counts) != set(EXPECTED_GROUPS):
            raise AssertionError(f"service inventory group count keys mismatch: {payload}")
        expected_counts = dict(Counter(item["group"] for item in services))
        expected_counts = {group: expected_counts.get(group, 0) for group in EXPECTED_GROUPS}
        if group_counts != expected_counts:
            raise AssertionError(f"service inventory group counts mismatch: {payload}")
        if sum(group_counts.values()) != len(services):
            raise AssertionError(f"service inventory group counts do not cover files: {payload}")

        state = request("GET", "/state")
        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/service-inventory" not in state_routes:
            raise AssertionError(f"state route list missing service inventory route: {state_routes}")

        index = request("GET", "/qa/coverage-index", timeout=120.0)
        app_group = (index.get("groups") or {}).get("appState") or {}
        if app_group.get("serviceInventoryFileCount") != payload.get("serviceFileCount"):
            raise AssertionError(f"coverage index service file count mismatch: {index}")
        if app_group.get("serviceInventoryFunctionCount") != payload.get("functionCount"):
            raise AssertionError(f"coverage index service function count mismatch: {index}")
        if app_group.get("serviceInventoryGroupCounts") != payload.get("groupCounts"):
            raise AssertionError(f"coverage index service group counts mismatch: {index}")
        if app_group.get("serviceInventoryProofFileParity") != payload.get("proofFileParity"):
            raise AssertionError(f"coverage index service proof parity mismatch: {index}")

        proofs = payload.get("proofs") or []
        if proofs != EXPECTED_PROOFS:
            raise AssertionError(f"service inventory proof list mismatch: {payload}")
        if payload.get("proofCount") != len(EXPECTED_PROOFS):
            raise AssertionError(f"service inventory proof count mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"service inventory proof-file parity mismatch: {payload}")
        missing_files = sorted(name for name in EXPECTED_PROOFS if not (ROOT / "scripts" / name).is_file())
        if missing_files:
            raise AssertionError(f"service inventory names missing proof files: {missing_files}")

        print("service-inventory proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"service-inventory proof failed: {exc}", flush=True)
        raise SystemExit(1)
