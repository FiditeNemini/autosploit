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

EXPECTED_CATEGORIES = [
    "engine",
    "model",
    "runtime",
    "context",
    "cache",
    "agents",
    "cves",
    "tools",
    "logs",
]

REQUIRED_ROUTES = {
    "/qa/seed-settings-visual-state",
    "/qa/settings-category",
    "/qa/apply-app-settings",
    "/qa/seed-live-cache-stats",
    "/qa/seed-cve-settings-status",
    "/qa/cve-settings-action",
    "/qa/cve-settings-add-panel",
    "/qa/seed-tool-settings-status",
    "/qa/tool-settings-action",
    "/qa/seed-inference-log-actions",
    "/qa/inference-log-action",
    "/qa/agent-settings-action",
}

REQUIRED_CONTRACTS = {
    "splitCategoryPages",
    "appOnlyApplyNoEngineRestart",
    "engineStartStopActionState",
    "modelFolderWarning",
    "runtimeParserAutodetect",
    "contextControls",
    "cacheTopologyStatus",
    "agentControls",
    "cveStatusAndActions",
    "toolStatusAndActions",
    "inferenceLogActions",
    "visualSettingsProofs",
}

REQUIRED_PROOFS = {
    "settings-category-coverage-proof.py",
    "settings-apply-proof.py",
    "settings-engine-actions-proof.py",
    "model-folder-warning-proof.py",
    "cache-stats-state-proof.py",
    "live-cache-stats-ui-proof.py",
    "agent-settings-actions-proof.py",
    "cve-settings-status-proof.py",
    "cve-settings-actions-proof.py",
    "cve-settings-add-panel-proof.py",
    "tool-settings-status-proof.py",
    "tool-settings-actions-proof.py",
    "inference-log-actions-proof.py",
    "visual-settings-proof.py",
    "visual-cve-settings-status-proof.py",
    "visual-tool-settings-status-proof.py",
    "visual-live-cache-stats-proof.py",
}

REQUIRED_VISUAL_MANIFESTS = {
    "docs/visual-proofs/checkpoint-69/manifest.json",
    "docs/visual-proofs/checkpoint-90/manifest.json",
    "docs/visual-proofs/checkpoint-101/manifest.json",
    "docs/visual-proofs/checkpoint-107/manifest.json",
    "docs/visual-proofs/checkpoint-108/manifest.json",
    "docs/visual-proofs/checkpoint-109/manifest.json",
}

REQUIRED_SETTINGS_SURFACES = [
    "engineModelRuntime",
    "contextAndCache",
    "agentControls",
    "cveDatabase",
    "toolInventory",
    "inferenceLogs",
    "visualStatusProofs",
]

REQUIRED_SETTINGS_SURFACE_PROOFS = {
    "engineModelRuntime": [
        "settings-category-coverage-proof.py",
        "settings-apply-proof.py",
        "settings-engine-actions-proof.py",
        "model-folder-warning-proof.py",
    ],
    "contextAndCache": ["cache-stats-state-proof.py", "live-cache-stats-ui-proof.py"],
    "agentControls": ["agent-settings-actions-proof.py"],
    "cveDatabase": [
        "cve-settings-status-proof.py",
        "cve-settings-actions-proof.py",
        "cve-settings-add-panel-proof.py",
    ],
    "toolInventory": ["tool-settings-status-proof.py", "tool-settings-actions-proof.py"],
    "inferenceLogs": ["inference-log-actions-proof.py"],
    "visualStatusProofs": [
        "visual-settings-proof.py",
        "visual-cve-settings-status-proof.py",
        "visual-tool-settings-status-proof.py",
        "visual-live-cache-stats-proof.py",
    ],
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


def assert_manifest_has_captures(manifest_path: str) -> None:
    path = ROOT / manifest_path
    if not path.is_file():
        raise AssertionError(f"settings coverage names missing visual manifest: {manifest_path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("ok") is not True:
        raise AssertionError(f"settings coverage visual manifest is not ok: {manifest_path}")
    captures = manifest.get("captures") or []
    if not captures:
        raise AssertionError(f"settings coverage visual manifest has no captures: {manifest_path}")
    missing = [capture for capture in captures if not (ROOT / capture).is_file()]
    if missing:
        raise AssertionError(f"settings coverage visual manifest names missing captures: {missing}")


def assert_settings_coverage() -> None:
    state = request("GET", "/state")
    coverage = request("GET", "/qa/settings-coverage")

    if coverage.get("ok") is not True:
        raise AssertionError(f"/qa/settings-coverage failed: {coverage}")

    categories = coverage.get("categories") or []
    category_ids = [item.get("id") for item in categories]
    if category_ids != EXPECTED_CATEGORIES:
        raise AssertionError(f"settings coverage category order mismatch: {category_ids}")
    for item in categories:
        if not item.get("pageSections"):
            raise AssertionError(f"settings coverage category missing sections: {item}")

    routes = set(coverage.get("routes") or [])
    missing_routes = sorted(REQUIRED_ROUTES.difference(routes))
    if missing_routes:
        raise AssertionError(f"settings coverage missing routes {missing_routes}: {coverage}")

    contracts = coverage.get("contracts") or {}
    missing_contracts = sorted(name for name in REQUIRED_CONTRACTS if contracts.get(name) is not True)
    if missing_contracts:
        raise AssertionError(f"settings coverage missing contracts {missing_contracts}: {coverage}")

    proofs = set(coverage.get("proofs") or [])
    missing_proofs = sorted(REQUIRED_PROOFS.difference(proofs))
    if missing_proofs:
        raise AssertionError(f"settings coverage missing proofs {missing_proofs}: {coverage}")
    if coverage.get("proofCount", 0) < len(REQUIRED_PROOFS):
        raise AssertionError(f"settings coverage proof count mismatch: {coverage}")
    missing_files = sorted(name for name in REQUIRED_PROOFS if not (ROOT / "scripts" / name).is_file())
    if missing_files:
        raise AssertionError(f"settings coverage names non-existent proof files: {missing_files}")
    if coverage.get("proofFileParity") is not True:
        raise AssertionError(f"settings coverage proof file parity mismatch: {coverage}")
    manifests = set(coverage.get("visualManifests") or [])
    missing_manifests = sorted(REQUIRED_VISUAL_MANIFESTS.difference(manifests))
    if missing_manifests:
        raise AssertionError(f"settings coverage missing visual manifests {missing_manifests}: {coverage}")
    for manifest in REQUIRED_VISUAL_MANIFESTS:
        assert_manifest_has_captures(manifest)

    if coverage.get("categoryCount") != len(EXPECTED_CATEGORIES):
        raise AssertionError(f"settings coverage category count mismatch: {coverage}")
    if coverage.get("cacheResponseMethod") != "prefix-cache-l2-turboquant":
        raise AssertionError(f"settings coverage cache method mismatch: {coverage}")
    if coverage.get("supportedFamilies") != ["qwen", "minimax"]:
        raise AssertionError(f"settings coverage supported family mismatch: {coverage}")
    if coverage.get("settingsSurfaces") != REQUIRED_SETTINGS_SURFACES:
        raise AssertionError(f"settings coverage surface list mismatch: {coverage}")
    if coverage.get("settingsSurfaceCount") != len(REQUIRED_SETTINGS_SURFACES):
        raise AssertionError(f"settings coverage surface count mismatch: {coverage}")
    if coverage.get("settingsSurfaceParity") is not True:
        raise AssertionError(f"settings coverage surface parity mismatch: {coverage}")
    if coverage.get("settingsSurfaceProofs") != REQUIRED_SETTINGS_SURFACE_PROOFS:
        raise AssertionError(f"settings coverage surface proof map mismatch: {coverage}")
    if coverage.get("settingsSurfaceProofCount") != len(REQUIRED_SETTINGS_SURFACE_PROOFS):
        raise AssertionError(f"settings coverage surface proof count mismatch: {coverage}")
    if coverage.get("settingsSurfaceProofParity") is not True:
        raise AssertionError(f"settings coverage surface proof parity mismatch: {coverage}")
    for surface, proof_names in REQUIRED_SETTINGS_SURFACE_PROOFS.items():
        missing_surface_files = sorted(name for name in proof_names if not (ROOT / "scripts" / name).is_file())
        if missing_surface_files:
            raise AssertionError(f"settings surface {surface} names missing proof files {missing_surface_files}: {coverage}")

    qa = state.get("qaCoverage") or {}
    if "/qa/settings-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing settings coverage route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_settings_coverage()
        print("settings-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"settings-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
