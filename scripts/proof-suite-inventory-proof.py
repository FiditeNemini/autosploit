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
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"

SPECIAL_PROOFS = {
    "live-turn-harness.py",
    "verify-live-models.py",
    "prove-parser-api.py",
    "prove-block-l2-cache.py",
    "prove-ssm-rederive-status.py",
}

EXPECTED_GROUPS = {
    "appStateInventory",
    "agentAndChat",
    "contextAndEvidence",
    "runtimeAndCache",
    "settingsAndVisuals",
    "toolsAndParsers",
    "tabsAndSessions",
    "releaseReadiness",
    "visualProofs",
    "liveModelProofs",
    "supportAndData",
}

REQUIRED_ROUTE_TARGETS = {
    "/qa/coverage-index",
    "/qa/proof-ledger",
    "/qa/runtime-coverage",
    "/qa/python-runtime-inventory",
    "/qa/agent-flow-inventory",
    "/qa/visual-coverage",
    "/qa/result-parser-coverage",
    "/qa/tool-family-fanout-coverage",
    "/qa/release-readiness",
    "/qa/beta-readiness-coverage",
}

REQUIRED_PROOF_FILES = {
    "proof-suite-inventory-proof.py",
    "proof-ledger-proof.py",
    "coverage-index-proof.py",
    "app-qa-matrix-smoke-proof.py",
    "runtime-coverage-proof.py",
    "python-runtime-inventory-proof.py",
    "agent-flow-inventory-proof.py",
    "visual-coverage-proof.py",
    "live-turn-harness.py",
    "verify-live-models.py",
}


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


def expected_proof_files() -> list[Path]:
    return sorted(
        path
        for path in (ROOT / "scripts").glob("*.py")
        if path.name.endswith("-proof.py") or path.name in SPECIAL_PROOFS
    )


def expected_group(file_name: str) -> str:
    if file_name in {"live-turn-harness.py", "verify-live-models.py"} or file_name.startswith("live-"):
        return "liveModelProofs"
    if file_name.startswith("visual-") or "screenshot" in file_name:
        return "visualProofs"
    if any(token in file_name for token in ("release", "beta-readiness", "notar", "package")):
        return "releaseReadiness"
    if any(token in file_name for token in ("runtime", "cache", "model", "qwen", "prove-", "python-runtime")):
        return "runtimeAndCache"
    if any(token in file_name for token in ("tool", "parser", "fanout")):
        return "toolsAndParsers"
    if any(token in file_name for token in ("context", "evidence", "cve", "catalog", "stash-retrieval")):
        return "contextAndEvidence"
    if any(token in file_name for token in ("settings", "inference-log", "theme")):
        return "settingsAndVisuals"
    if any(token in file_name for token in ("agent", "chat", "turn")):
        return "agentAndChat"
    if any(
        token in file_name
        for token in (
            "recon",
            "web",
            "network",
            "creds",
            "exploit",
            "post",
            "osint",
            "report",
            "stash",
            "subtab",
            "tab-action",
            "phase",
            "sidebar",
            "onboarding",
            "persistence",
            "window-overlay",
            "activity-feed",
            "mode-selection",
        )
    ):
        return "tabsAndSessions"
    if any(token in file_name for token in ("endpoint", "action-state", "function-flow", "view", "service", "proof-ledger", "artifact-ledger", "checkpoint-ledger", "audit-ledger", "gap-ledger", "coverage-index", "docs-inventory", "app-qa")):
        return "appStateInventory"
    return "supportAndData"


def script_summary(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise AssertionError(f"{path.name} must parse with ast: {exc}") from exc
    functions = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    route_targets = sorted(set(re.findall(r'"(/(?:qa/)?[A-Za-z0-9_./-]+)"', text)))
    return {
        "file": path.name,
        "group": expected_group(path.name),
        "functionCount": len(functions),
        "classCount": len(classes),
        "routeTargets": route_targets,
        "routeTargetCount": len(route_targets),
        "launchesApp": "build_and_run.sh" in text or "wait_for_app(" in text or "APP_API" in text,
        "visualCapture": "screencapture" in text
        or path.name.startswith("visual-")
        or "screenshot" in path.name,
        "liveModel": path.name in {"live-turn-harness.py", "verify-live-models.py"} or "live" in path.name or "--model" in text,
    }


def assert_proof_suite_inventory() -> None:
    state = request("GET", "/state")
    inventory = request("GET", "/qa/proof-suite-inventory")
    index = request("GET", "/qa/coverage-index")

    expected = [script_summary(path) for path in expected_proof_files()]
    expected_names = [item["file"] for item in expected]
    expected_group_counts: dict[str, int] = {name: 0 for name in EXPECTED_GROUPS}
    for item in expected:
        expected_group_counts[item["group"]] = expected_group_counts.get(item["group"], 0) + 1
    expected_routes = sorted({route for item in expected for route in item["routeTargets"]})
    expected_launches_app = sum(1 for item in expected if item["launchesApp"])
    expected_visual = sum(1 for item in expected if item["visualCapture"])
    expected_live = sum(1 for item in expected if item["liveModel"])
    expected_functions = sum(int(item["functionCount"]) for item in expected)

    if inventory.get("ok") is not True:
        raise AssertionError(f"/qa/proof-suite-inventory failed: {inventory}")
    if inventory.get("route") != "/qa/proof-suite-inventory":
        raise AssertionError(f"proof-suite route mismatch: {inventory}")
    if inventory.get("sourceRoot") != "scripts":
        raise AssertionError(f"proof-suite source root mismatch: {inventory}")
    if inventory.get("proofPattern") != "*-proof.py + special harness proofs":
        raise AssertionError(f"proof-suite pattern mismatch: {inventory}")
    if inventory.get("fileCount") != len(expected):
        raise AssertionError(f"proof-suite file count mismatch expected {len(expected)}: {inventory}")
    if inventory.get("proofs") != expected_names:
        raise AssertionError(f"proof-suite proof list mismatch: {inventory}")
    if inventory.get("proofFileParity") is not True:
        raise AssertionError(f"proof-suite proof file parity mismatch: {inventory}")
    if inventory.get("parseParity") is not True:
        raise AssertionError(f"proof-suite parse parity mismatch: {inventory}")
    if inventory.get("groupCounts") != expected_group_counts:
        raise AssertionError(f"proof-suite group counts mismatch: {inventory}")
    if set(inventory.get("groups") or []) != EXPECTED_GROUPS:
        raise AssertionError(f"proof-suite group set mismatch: {inventory}")
    if inventory.get("groupParity") is not True:
        raise AssertionError(f"proof-suite group parity mismatch: {inventory}")
    if inventory.get("routeTargets") != expected_routes:
        raise AssertionError(f"proof-suite route target list mismatch: {inventory}")
    if inventory.get("routeTargetCount") != len(expected_routes):
        raise AssertionError(f"proof-suite route target count mismatch: {inventory}")
    if not REQUIRED_ROUTE_TARGETS.issubset(set(inventory.get("routeTargets") or [])):
        raise AssertionError(f"proof-suite missing required route targets: {inventory}")
    if inventory.get("launchesAppCount") != expected_launches_app:
        raise AssertionError(f"proof-suite launches-app count mismatch: {inventory}")
    if inventory.get("visualProofCount") != expected_visual:
        raise AssertionError(f"proof-suite visual proof count mismatch: {inventory}")
    if inventory.get("liveModelProofCount") != expected_live:
        raise AssertionError(f"proof-suite live model proof count mismatch: {inventory}")
    if inventory.get("functionCount") != expected_functions:
        raise AssertionError(f"proof-suite function count mismatch: {inventory}")
    if inventory.get("functionCount", 0) < 250:
        raise AssertionError(f"proof-suite function inventory too low: {inventory}")
    if inventory.get("launchesAppCount", 0) < 100:
        raise AssertionError(f"proof-suite app-launching proof count too low: {inventory}")
    if inventory.get("visualProofCount", 0) < 20:
        raise AssertionError(f"proof-suite visual proof count too low: {inventory}")
    if inventory.get("liveModelProofCount", 0) < 3:
        raise AssertionError(f"proof-suite live model proof count too low: {inventory}")
    if inventory.get("routeTargetCount", 0) < 45:
        raise AssertionError(f"proof-suite route target count too low: {inventory}")
    for required in REQUIRED_PROOF_FILES:
        if required not in expected_names:
            raise AssertionError(f"expected proof file missing on disk: {required}")
        if required not in (inventory.get("proofs") or []):
            raise AssertionError(f"proof-suite missing required proof file: {required}")
    files_by_name = {item.get("file"): item for item in inventory.get("files") or []}
    for name in REQUIRED_PROOF_FILES:
        payload = files_by_name.get(name)
        if not payload:
            raise AssertionError(f"proof-suite missing file detail for {name}: {inventory}")
        if payload.get("group") != expected_group(name):
            raise AssertionError(f"proof-suite file group mismatch for {name}: {payload}")
        if payload.get("functionCount", 0) <= 0:
            raise AssertionError(f"proof-suite file has no parsed functions for {name}: {payload}")
    qa = state.get("qaCoverage") or {}
    if "/qa/proof-suite-inventory" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing proof-suite route contract: {qa}")
    groups = index.get("groups") or {}
    app_state_group = groups.get("appState") or {}
    if "/qa/proof-suite-inventory" not in (app_state_group.get("endpoints") or []):
        raise AssertionError(f"coverage index app state missing proof-suite endpoint: {app_state_group}")
    if "proof-suite-inventory-proof.py" not in (app_state_group.get("proofs") or []):
        raise AssertionError(f"coverage index app state missing proof-suite proof: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryFileCount") != inventory.get("fileCount"):
        raise AssertionError(f"coverage index proof-suite file count mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryGroupCounts") != inventory.get("groupCounts"):
        raise AssertionError(f"coverage index proof-suite group counts mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryRouteTargetCount") != inventory.get("routeTargetCount"):
        raise AssertionError(f"coverage index proof-suite route target count mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryLaunchesAppCount") != inventory.get("launchesAppCount"):
        raise AssertionError(f"coverage index proof-suite launches-app count mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryVisualProofCount") != inventory.get("visualProofCount"):
        raise AssertionError(f"coverage index proof-suite visual count mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryLiveModelProofCount") != inventory.get("liveModelProofCount"):
        raise AssertionError(f"coverage index proof-suite live count mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryProofFileParity") != inventory.get("proofFileParity"):
        raise AssertionError(f"coverage index proof-suite file parity mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryParseParity") != inventory.get("parseParity"):
        raise AssertionError(f"coverage index proof-suite parse parity mismatch: {app_state_group}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_proof_suite_inventory()
        print("proof-suite-inventory proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"proof-suite-inventory proof failed: {exc}", flush=True)
        raise SystemExit(1)
