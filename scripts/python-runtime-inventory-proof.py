#!/usr/bin/env python3
from __future__ import annotations

import ast
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

EXPECTED_GROUPS = [
    "engineRuntime",
    "apiAdapters",
    "reasoningParsers",
    "toolParsers",
    "cacheAndSSM",
    "engineTests",
    "qaProofs",
    "dataPipelines",
]

EXPECTED_PROOFS = [
    "python-runtime-inventory-proof.py",
    "app-qa-matrix-smoke-proof.py",
    "coverage-index-proof.py",
    "runtime-coverage-proof.py",
    "engine-python-runtime-resolution-proof.py",
    "prove-parser-api.py",
    "result-parser-routing-proof.py",
    "tool-flow-coverage-proof.py",
    "prove-block-l2-cache.py",
    "prove-ssm-rederive-status.py",
    "verify-live-models.py",
]


def py_files() -> list[Path]:
    roots = [ROOT / "ExploitBotEngine", ROOT / "scripts"]
    files: list[Path] = []
    for root in roots:
        files.extend(
            path
            for path in root.rglob("*.py")
            if "__pycache__" not in path.parts
            and not any(part.startswith(".") for part in path.relative_to(ROOT).parts)
            and ".egg-info" not in path.parts
        )
    return sorted(files)


def group_for(path: Path) -> str:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    rel_s = str(rel)
    if parts[0] == "scripts":
        if path.name in {"build-cve-db.py", "generate-embeddings.py"}:
            return "dataPipelines"
        return "qaProofs"
    if "testsuite" in parts:
        return "engineTests"
    if "reasoning" in parts:
        return "reasoningParsers"
    if "tool_parsers" in parts:
        return "toolParsers"
    if any(token in rel_s for token in ("cache", "ssm", "mamba", "disk_store", "kv_quantization")):
        return "cacheAndSSM"
    if "/api/" in rel_s:
        return "apiAdapters"
    return "engineRuntime"


def proof_for(group: str) -> str:
    return {
        "engineRuntime": "runtime-coverage-proof.py",
        "apiAdapters": "prove-parser-api.py",
        "reasoningParsers": "prove-parser-api.py",
        "toolParsers": "result-parser-routing-proof.py",
        "cacheAndSSM": "prove-block-l2-cache.py",
        "engineTests": "runtime-coverage-proof.py",
        "qaProofs": "app-qa-matrix-smoke-proof.py",
        "dataPipelines": "context-coverage-proof.py",
    }[group]


def parse_file(path: Path) -> dict[str, object]:
    rel = str(path.relative_to(ROOT))
    source = path.read_text(encoding="utf-8")
    try:
        ast.parse(source)
        parse_ok = True
    except SyntaxError:
        parse_ok = False
    classes = re.findall(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)", source, re.MULTILINE)
    functions = re.findall(
        r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        source,
        re.MULTILINE,
    )
    group = group_for(path)
    return {
        "file": rel,
        "group": group,
        "proofOwner": proof_for(group),
        "classes": classes,
        "classCount": len(classes),
        "functions": functions,
        "functionCount": len(functions),
        "parseOK": parse_ok,
    }


def source_inventory() -> list[dict[str, object]]:
    return [parse_file(path) for path in py_files()]


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
        payload = request("GET", "/qa/python-runtime-inventory")
        if payload.get("ok") is not True:
            raise AssertionError(f"python runtime inventory route failed: {payload}")
        if payload.get("sourceRoots") != ["ExploitBotEngine", "scripts"]:
            raise AssertionError(f"python runtime inventory source roots mismatch: {payload}")
        if payload.get("files") != inventory:
            raise AssertionError(f"python runtime inventory file list mismatch: {payload}")
        if payload.get("fileCount") != len(inventory):
            raise AssertionError(f"python runtime inventory file count mismatch: {payload}")
        if payload.get("classCount") != sum(item["classCount"] for item in inventory):
            raise AssertionError(f"python runtime inventory class count mismatch: {payload}")
        if payload.get("functionCount") != sum(item["functionCount"] for item in inventory):
            raise AssertionError(f"python runtime inventory function count mismatch: {payload}")
        if payload.get("parseParity") is not True:
            raise AssertionError(f"python runtime inventory parse parity mismatch: {payload}")
        if payload.get("functionCount", 0) < 500:
            raise AssertionError(f"python runtime inventory function count too low: {payload}")
        if any(not item.get("proofOwner") for item in payload.get("files") or []):
            raise AssertionError(f"python runtime inventory missing proof owner: {payload}")

        if payload.get("groups") != EXPECTED_GROUPS:
            raise AssertionError(f"python runtime inventory group list mismatch: {payload}")
        group_counts = payload.get("groupCounts") or {}
        if set(group_counts) != set(EXPECTED_GROUPS):
            raise AssertionError(f"python runtime inventory group count keys mismatch: {payload}")
        expected_counts = dict(Counter(item["group"] for item in inventory))
        expected_counts = {group: expected_counts.get(group, 0) for group in EXPECTED_GROUPS}
        if group_counts != expected_counts:
            raise AssertionError(f"python runtime inventory group counts mismatch: {payload}")

        state = request("GET", "/state")
        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/python-runtime-inventory" not in state_routes:
            raise AssertionError(f"state route list missing python runtime inventory route: {state_routes}")

        index = request("GET", "/qa/coverage-index")
        runtime_group = (index.get("groups") or {}).get("runtimeAndCache") or {}
        if runtime_group.get("pythonRuntimeInventoryFileCount") != payload.get("fileCount"):
            raise AssertionError(f"coverage index python runtime file count mismatch: {index}")
        if runtime_group.get("pythonRuntimeInventoryFunctionCount") != payload.get("functionCount"):
            raise AssertionError(f"coverage index python runtime function count mismatch: {index}")
        if runtime_group.get("pythonRuntimeInventoryGroupCounts") != payload.get("groupCounts"):
            raise AssertionError(f"coverage index python runtime group count mismatch: {index}")
        if runtime_group.get("pythonRuntimeInventoryProofFileParity") != payload.get("proofFileParity"):
            raise AssertionError(f"coverage index python runtime proof parity mismatch: {index}")

        proofs = payload.get("proofs") or []
        if proofs != EXPECTED_PROOFS:
            raise AssertionError(f"python runtime inventory proof list mismatch: {payload}")
        if payload.get("proofCount") != len(EXPECTED_PROOFS):
            raise AssertionError(f"python runtime inventory proof count mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"python runtime inventory proof-file parity mismatch: {payload}")

        print("python-runtime-inventory proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"python-runtime-inventory proof failed: {exc}", flush=True)
        raise SystemExit(1)
