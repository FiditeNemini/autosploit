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
MODEL_ROOT = ROOT / "ExploitBot" / "Sources" / "ExploitBot" / "Models"

EXPECTED_GROUPS = [
    "appStateCore",
    "operationModels",
    "navigationModels",
    "chatModels",
    "parsedResultModels",
]

EXPECTED_PROOFS = [
    "model-state-inventory-proof.py",
    "action-state-inventory-proof.py",
    "endpoint-inventory-proof.py",
    "tab-action-coverage-proof.py",
    "result-parser-routing-proof.py",
    "app-qa-matrix-smoke-proof.py",
]

EXPECTED_ENUMS = {
    "OpStatus": ["active", "paused", "complete"],
    "InteractionMode": ["autopilot", "copilot", "manual"],
    "PentestPhase": ["scan", "detect", "breach"],
    "ToolTab": ["recon", "web", "network", "creds", "exploit", "post", "supplyChain", "osint", "report", "stash"],
}


def model_files() -> list[Path]:
    return sorted(MODEL_ROOT.glob("*.swift"))


def group_for(path: Path) -> str:
    name = path.name
    if name == "AppState.swift":
        return "appStateCore"
    if name == "Op.swift":
        return "operationModels"
    if name in {"ToolTab.swift", "PentestPhase.swift"}:
        return "navigationModels"
    if name == "ChatRole.swift":
        return "chatModels"
    if name == "ToolResult.swift":
        return "parsedResultModels"
    return "appStateCore"


def proof_for(group: str) -> str:
    return {
        "appStateCore": "endpoint-inventory-proof.py",
        "operationModels": "action-state-inventory-proof.py",
        "navigationModels": "tab-action-coverage-proof.py",
        "chatModels": "app-qa-matrix-smoke-proof.py",
        "parsedResultModels": "result-parser-routing-proof.py",
    }[group]


def capture(pattern: str, source: str) -> list[str]:
    return re.findall(pattern, source, flags=re.MULTILINE)


def parse_enum_cases(source: str) -> dict[str, list[str]]:
    cases: dict[str, list[str]] = {}
    enum_pattern = re.compile(r"enum\s+([A-Za-z_][A-Za-z0-9_]*)[^{]*\{(?P<body>.*?)\n\}", re.DOTALL)
    for match in enum_pattern.finditer(source):
        enum_name = match.group(1)
        body = match.group("body")
        names: list[str] = []
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("case "):
                continue
            stripped = stripped.removeprefix("case ")
            for part in stripped.split(","):
                name = re.split(r"\s|=", part.strip(), maxsplit=1)[0].strip()
                if name and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
                    names.append(name)
        if names:
            cases[enum_name] = names
    return cases


def parse_file(path: Path) -> dict[str, object]:
    source = path.read_text(encoding="utf-8")
    rel = str(path.relative_to(ROOT))
    group = group_for(path)
    types = [
        {"kind": kind, "name": name}
        for kind, name in re.findall(r"^\s*(struct|class|enum|protocol)\s+([A-Za-z_][A-Za-z0-9_]*)", source, flags=re.MULTILINE)
    ]
    functions = capture(r"^\s*(?:private\s+|static\s+|@MainActor\s+|mutating\s+|nonisolated\s+|override\s+|class\s+|final\s+)*func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source)
    enum_cases = parse_enum_cases(source)
    return {
        "file": rel,
        "group": group,
        "proofOwner": proof_for(group),
        "types": types,
        "typeCount": len(types),
        "functions": functions,
        "functionCount": len(functions),
        "enumCases": enum_cases,
        "enumCaseCount": sum(len(values) for values in enum_cases.values()),
    }


def source_inventory() -> list[dict[str, object]]:
    return [parse_file(path) for path in model_files()]


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


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        inventory = source_inventory()
        payload = request("GET", "/qa/model-state-inventory")
        if payload.get("ok") is not True:
            raise AssertionError(f"model state inventory route failed: {payload}")
        if payload.get("sourceRoot") != "ExploitBot/Sources/ExploitBot/Models":
            raise AssertionError(f"model state inventory source root mismatch: {payload}")
        if payload.get("files") != inventory:
            raise AssertionError(f"model state inventory file list mismatch: {payload}")
        if payload.get("fileCount") != len(inventory):
            raise AssertionError(f"model state inventory file count mismatch: {payload}")
        if payload.get("typeCount") != sum(item["typeCount"] for item in inventory):
            raise AssertionError(f"model state inventory type count mismatch: {payload}")
        if payload.get("functionCount") != sum(item["functionCount"] for item in inventory):
            raise AssertionError(f"model state inventory function count mismatch: {payload}")
        if payload.get("enumCaseCount") != sum(item["enumCaseCount"] for item in inventory):
            raise AssertionError(f"model state inventory enum case count mismatch: {payload}")

        if payload.get("groups") != EXPECTED_GROUPS:
            raise AssertionError(f"model state inventory groups mismatch: {payload}")
        group_counts = payload.get("groupCounts") or {}
        expected_counts = dict(Counter(item["group"] for item in inventory))
        expected_counts = {group: expected_counts.get(group, 0) for group in EXPECTED_GROUPS}
        if group_counts != expected_counts:
            raise AssertionError(f"model state inventory group counts mismatch: {payload}")

        enum_cases = payload.get("enumCases") or {}
        for name, cases in EXPECTED_ENUMS.items():
            if enum_cases.get(name) != cases:
                raise AssertionError(f"model state inventory enum case mismatch for {name}: {payload}")

        state = request("GET", "/state")
        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/model-state-inventory" not in state_routes:
            raise AssertionError(f"state route list missing model state inventory route: {state_routes}")

        index = request("GET", "/qa/coverage-index")
        app_group = (index.get("groups") or {}).get("appState") or {}
        if app_group.get("modelStateInventoryFileCount") != payload.get("fileCount"):
            raise AssertionError(f"coverage index model state file count mismatch: {index}")
        if app_group.get("modelStateInventoryTypeCount") != payload.get("typeCount"):
            raise AssertionError(f"coverage index model state type count mismatch: {index}")
        if app_group.get("modelStateInventoryFunctionCount") != payload.get("functionCount"):
            raise AssertionError(f"coverage index model state function count mismatch: {index}")
        if app_group.get("modelStateInventoryGroupCounts") != payload.get("groupCounts"):
            raise AssertionError(f"coverage index model state group count mismatch: {index}")
        if app_group.get("modelStateInventoryProofFileParity") != payload.get("proofFileParity"):
            raise AssertionError(f"coverage index model state proof parity mismatch: {index}")

        proofs = payload.get("proofs") or []
        if proofs != EXPECTED_PROOFS:
            raise AssertionError(f"model state inventory proof list mismatch: {payload}")
        if payload.get("proofCount") != len(EXPECTED_PROOFS):
            raise AssertionError(f"model state inventory proof count mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"model state inventory proof-file parity mismatch: {payload}")

        print("model-state-inventory proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"model-state-inventory proof failed: {exc}", flush=True)
        raise SystemExit(1)
