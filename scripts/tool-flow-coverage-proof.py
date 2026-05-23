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

EXPECTED_ROUTES = {
    "/qa/tool-coverage",
    "/qa/tool-catalog",
    "/qa/seed-result-parser-fixture",
    "/qa/result-parser-coverage",
    "/qa/seed-tool-family-fanout-fixture",
    "/qa/tool-family-fanout-coverage",
}
EXPECTED_PROOFS = {
    "tool-registry-coverage-proof.py",
    "tool-catalog-proof.py",
    "result-parser-routing-proof.py",
    "result-context-catalog-proof.py",
    "tool-fanout-status-proof.py",
    "tool-family-fanout-coverage-proof.py",
    "visual-chat-interaction-proof.py",
    "activity-feed-actions-proof.py",
    "visual-tab-proof.py",
    "visual-context-inspector-proof.py",
    "chat-tool-output-expand-proof.py",
}
EXPECTED_FAMILIES = {"recon", "web", "network", "creds", "exploit", "post", "osint"}
EXPECTED_STATE_KEYS = {
    "messages.toolCards",
    "tabActivities",
    "feedRecent",
    "contextCatalog",
    "results",
}
EXPECTED_VISUAL_SURFACES = [
    "chatToolCard",
    "activityFeedStatus",
    "tabStatusIndicator",
    "parsedResultRow",
    "contextCatalogHit",
    "toolOutputExpansion",
]

EXPECTED_VISUAL_SURFACE_PROOFS = {
    "chatToolCard": ["visual-chat-interaction-proof.py", "tool-fanout-status-proof.py"],
    "activityFeedStatus": ["activity-feed-actions-proof.py", "tool-fanout-status-proof.py"],
    "tabStatusIndicator": ["visual-tab-proof.py", "tool-family-fanout-coverage-proof.py"],
    "parsedResultRow": ["result-parser-routing-proof.py", "tool-family-fanout-coverage-proof.py"],
    "contextCatalogHit": ["result-context-catalog-proof.py", "visual-context-inspector-proof.py"],
    "toolOutputExpansion": ["chat-tool-output-expand-proof.py", "visual-chat-interaction-proof.py"],
}

EXPECTED_TAB_ACTIVITY_STATUS_PROOFS = {
    "running": ["tool-fanout-status-proof.py", "visual-tab-proof.py"],
    "done": ["tool-family-fanout-coverage-proof.py", "tool-fanout-status-proof.py"],
    "failed": ["visual-tab-proof.py", "activity-feed-actions-proof.py"],
    "canceled": ["chat-turn-controls-proof.py", "visual-chat-interaction-proof.py"],
}


def request(method: str, path: str, body: str | dict | None = None, timeout: float = 8.0):
    if isinstance(body, dict):
        body = json.dumps(body)
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

        coverage = request("GET", "/qa/tool-flow-coverage")
        if coverage.get("ok") is not True:
            raise AssertionError(f"tool flow coverage route failed: {coverage}")
        if set(coverage.get("routes") or []) != EXPECTED_ROUTES:
            raise AssertionError(f"tool flow route contract mismatch: {coverage}")
        if not EXPECTED_PROOFS.issubset(set(coverage.get("proofs") or [])):
            raise AssertionError(f"tool flow proofs missing: {coverage}")
        if coverage.get("proofCount", 0) < len(EXPECTED_PROOFS):
            raise AssertionError(f"tool flow proof count mismatch: {coverage}")
        missing_files = sorted(name for name in EXPECTED_PROOFS if not (ROOT / "scripts" / name).is_file())
        if missing_files:
            raise AssertionError(f"tool flow names non-existent proof files: {missing_files}")
        if coverage.get("proofFileParity") is not True:
            raise AssertionError(f"tool flow proof file parity mismatch: {coverage}")
        if set(coverage.get("families") or []) != EXPECTED_FAMILIES:
            raise AssertionError(f"tool flow family coverage mismatch: {coverage}")
        if coverage.get("toolCount") != 38:
            raise AssertionError(f"tool flow did not expose registry count: {coverage}")
        if coverage.get("callbackCount") != 3:
            raise AssertionError(f"tool flow did not expose callback count: {coverage}")
        if coverage.get("toolSchemaCap") != 12:
            raise AssertionError(f"tool flow did not expose schema cap: {coverage}")
        if coverage.get("toolSchemaPolicy") != "prompt-tab-ranked-installed-cap":
            raise AssertionError(f"tool flow did not expose schema policy: {coverage}")
        if coverage.get("toolCatalogRoute") != "/qa/tool-catalog":
            raise AssertionError(f"tool flow did not expose tool catalog route: {coverage}")
        if coverage.get("structuredResultModeCount", 0) < 29:
            raise AssertionError(f"tool flow structured result mode count too low: {coverage}")
        if coverage.get("rawResultModeCount", 0) < 9:
            raise AssertionError(f"tool flow raw result mode count too low: {coverage}")
        if coverage.get("resultModeCountParity") is not True:
            raise AssertionError(f"tool flow result mode count parity mismatch: {coverage}")
        expected_activity_statuses = ["running", "done", "failed", "canceled"]
        if coverage.get("tabActivityStatuses") != expected_activity_statuses:
            raise AssertionError(f"tool flow tab activity statuses mismatch: {coverage}")
        if coverage.get("tabActivityStatusCount") != len(expected_activity_statuses):
            raise AssertionError(f"tool flow tab activity status count mismatch: {coverage}")
        if coverage.get("tabActivityStatusParity") is not True:
            raise AssertionError(f"tool flow tab activity status parity mismatch: {coverage}")
        if coverage.get("tabActivityIndicatorContract") != "status-dot-running-ring":
            raise AssertionError(f"tool flow tab activity indicator contract mismatch: {coverage}")
        if coverage.get("tabActivityStatusProofs") != EXPECTED_TAB_ACTIVITY_STATUS_PROOFS:
            raise AssertionError(f"tool flow tab activity status proof map mismatch: {coverage}")
        if coverage.get("tabActivityStatusProofCount") != len(EXPECTED_TAB_ACTIVITY_STATUS_PROOFS):
            raise AssertionError(f"tool flow tab activity status proof count mismatch: {coverage}")
        if coverage.get("tabActivityStatusProofParity") is not True:
            raise AssertionError(f"tool flow tab activity status proof parity mismatch: {coverage}")
        for status, proof_names in EXPECTED_TAB_ACTIVITY_STATUS_PROOFS.items():
            missing_status_files = sorted(name for name in proof_names if not (ROOT / "scripts" / name).is_file())
            if missing_status_files:
                raise AssertionError(f"tool tab activity status {status} names missing proof files {missing_status_files}: {coverage}")
        if coverage.get("tabActivityStatusProofFileParity") is not True:
            raise AssertionError(f"tool flow tab activity status proof-file parity mismatch: {coverage}")
        if coverage.get("toolVisualSurfaces") != EXPECTED_VISUAL_SURFACES:
            raise AssertionError(f"tool flow visual surfaces mismatch: {coverage}")
        if coverage.get("toolVisualSurfaceCount") != len(EXPECTED_VISUAL_SURFACES):
            raise AssertionError(f"tool flow visual surface count mismatch: {coverage}")
        if coverage.get("toolVisualSurfaceParity") is not True:
            raise AssertionError(f"tool flow visual surface parity mismatch: {coverage}")
        if coverage.get("toolVisualSurfaceProofs") != EXPECTED_VISUAL_SURFACE_PROOFS:
            raise AssertionError(f"tool flow visual surface proof map mismatch: {coverage}")
        if coverage.get("toolVisualSurfaceProofCount") != len(EXPECTED_VISUAL_SURFACE_PROOFS):
            raise AssertionError(f"tool flow visual surface proof count mismatch: {coverage}")
        if coverage.get("toolVisualSurfaceProofParity") is not True:
            raise AssertionError(f"tool flow visual surface proof parity mismatch: {coverage}")
        for surface, proof_names in EXPECTED_VISUAL_SURFACE_PROOFS.items():
            missing_surface_files = sorted(name for name in proof_names if not (ROOT / "scripts" / name).is_file())
            if missing_surface_files:
                raise AssertionError(f"tool visual surface {surface} names missing proof files {missing_surface_files}: {coverage}")
        if coverage.get("toolVisualSurfaceProofFileParity") is not True:
            raise AssertionError(f"tool flow visual surface proof-file parity mismatch: {coverage}")
        state_keys = set(coverage.get("stateKeys") or [])
        missing_state_keys = sorted(EXPECTED_STATE_KEYS.difference(state_keys))
        if missing_state_keys:
            raise AssertionError(f"tool flow missing state keys {missing_state_keys}: {coverage}")
        for key in ("registry", "parserRouting", "fanout", "contextCatalog"):
            if coverage.get("contracts", {}).get(key) is not True:
                raise AssertionError(f"tool flow contract missing {key}: {coverage}")

        registry = request("GET", "/qa/tool-coverage")
        if registry.get("ok") is not True:
            raise AssertionError(f"tool registry did not expose ok=true: {registry}")
        if registry.get("toolCount") != coverage.get("toolCount"):
            raise AssertionError(f"tool flow registry count disagrees with tool coverage: {coverage} {registry}")

        print("tool-flow-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"tool-flow-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
