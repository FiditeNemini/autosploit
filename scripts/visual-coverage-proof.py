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

REQUIRED_CONTRACTS = {
    "chatToolStates",
    "chatScrollLock",
    "settingsModelCache",
    "contextInspector",
    "requestAuditBadges",
    "tabActivity",
    "subtabLifecycle",
    "osintScreenshots",
    "reportExport",
    "stashRetrieval",
    "unsupportedModel",
    "postAttribution",
    "toolActionPanels",
    "liveCacheStats",
    "settingsCVEAndTools",
}

REQUIRED_PROOFS = {
    "visual-chat-proof.py",
    "visual-chat-interaction-proof.py",
    "visual-settings-proof.py",
    "visual-context-inspector-proof.py",
    "visual-request-audit-proof.py",
    "visual-tab-proof.py",
    "visual-osint-screenshot-proof.py",
    "visual-report-export-proof.py",
    "visual-stash-retrieval-proof.py",
    "visual-unsupported-model-proof.py",
    "visual-post-attribution-proof.py",
    "visual-web-verify-proof.py",
    "visual-recon-action-proof.py",
    "visual-network-protocol-proof.py",
    "visual-creds-action-proof.py",
    "visual-exploit-action-proof.py",
    "visual-report-agent-proof.py",
    "visual-live-cache-stats-proof.py",
    "visual-cve-settings-status-proof.py",
    "visual-tool-settings-status-proof.py",
}

REQUIRED_MANIFESTS = {
    "docs/visual-proofs/checkpoint-69/manifest.json",
    "docs/visual-proofs/checkpoint-70/manifest.json",
    "docs/visual-proofs/checkpoint-71/manifest.json",
    "docs/visual-proofs/checkpoint-72/manifest.json",
    "docs/visual-proofs/checkpoint-73/manifest.json",
    "docs/visual-proofs/checkpoint-84/manifest.json",
    "docs/visual-proofs/checkpoint-87/manifest.json",
    "docs/visual-proofs/checkpoint-90/manifest.json",
    "docs/visual-proofs/checkpoint-91/manifest.json",
    "docs/visual-proofs/checkpoint-92/manifest.json",
    "docs/visual-proofs/checkpoint-93/manifest.json",
    "docs/visual-proofs/checkpoint-94/manifest.json",
    "docs/visual-proofs/checkpoint-95/manifest.json",
    "docs/visual-proofs/checkpoint-96/manifest.json",
    "docs/visual-proofs/checkpoint-97/manifest.json",
    "docs/visual-proofs/checkpoint-98/manifest.json",
    "docs/visual-proofs/checkpoint-99/manifest.json",
    "docs/visual-proofs/checkpoint-100/manifest.json",
    "docs/visual-proofs/checkpoint-101/manifest.json",
    "docs/visual-proofs/checkpoint-107/manifest.json",
    "docs/visual-proofs/checkpoint-108/manifest.json",
    "docs/visual-proofs/checkpoint-109/manifest.json",
}

REQUIRED_ROUTES = {
    "/qa/seed-chat-visual-states",
    "/qa/chat-visual-mode",
    "/qa/chat-context-inspector",
    "/qa/seed-chat-request-audit-visual",
    "/qa/seed-visual-activity",
    "/qa/visual-subtab",
    "/qa/seed-settings-visual-state",
    "/qa/settings-category",
    "/qa/model-folder",
    "/qa/seed-live-cache-stats",
    "/qa/seed-cve-settings-status",
    "/qa/seed-tool-settings-status",
    "/qa/seed-osint-screenshot-artifact",
    "/qa/osint-artifact-action",
    "/qa/seed-post-attribution",
    "/qa/seed-web-verify-action",
    "/qa/seed-recon-action-status",
    "/qa/seed-network-protocol-action",
    "/qa/seed-creds-action-results",
    "/qa/seed-exploit-action-differentiation",
    "/qa/seed-report-export",
    "/qa/seed-report-agent-action",
    "/qa/seed-stash-retrieval",
    "/qa/context-packet",
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


def assert_visual_manifest(path: Path) -> int:
    if not path.is_file():
        raise AssertionError(f"missing visual manifest: {path.relative_to(ROOT)}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("ok") is not True:
        raise AssertionError(f"visual manifest is not ok: {path.relative_to(ROOT)} {manifest}")
    captures = manifest.get("captures") or []
    if not captures:
        raise AssertionError(f"visual manifest has no captures: {path.relative_to(ROOT)}")
    for capture in captures:
        capture_path = ROOT / capture
        if not capture_path.is_file():
            raise AssertionError(f"visual capture listed but missing: {capture}")
        if capture_path.stat().st_size < 10_000:
            raise AssertionError(f"visual capture too small to prove UI render: {capture}")
    return len(captures)


def assert_visual_coverage() -> None:
    state = request("GET", "/state")
    coverage = request("GET", "/qa/visual-coverage")

    if coverage.get("ok") is not True:
        raise AssertionError(f"/qa/visual-coverage failed: {coverage}")

    contracts = coverage.get("contracts") or {}
    missing_contracts = sorted(name for name in REQUIRED_CONTRACTS if contracts.get(name) is not True)
    if missing_contracts:
        raise AssertionError(f"visual coverage missing contracts {missing_contracts}: {coverage}")

    proofs = set(coverage.get("proofs") or [])
    missing_proofs = sorted(REQUIRED_PROOFS.difference(proofs))
    if missing_proofs:
        raise AssertionError(f"visual coverage missing proofs {missing_proofs}: {coverage}")
    missing_files = sorted(name for name in REQUIRED_PROOFS if not (ROOT / "scripts" / name).is_file())
    if missing_files:
        raise AssertionError(f"visual coverage names non-existent proof files: {missing_files}")
    if coverage.get("proofCount", 0) < len(REQUIRED_PROOFS):
        raise AssertionError(f"visual coverage proof count mismatch: {coverage}")
    missing_routes = sorted(REQUIRED_ROUTES.difference(set(coverage.get("routes") or [])))
    if missing_routes:
        raise AssertionError(f"visual coverage missing routes {missing_routes}: {coverage}")

    manifests = set(coverage.get("manifests") or [])
    missing_manifests = sorted(REQUIRED_MANIFESTS.difference(manifests))
    if missing_manifests:
        raise AssertionError(f"visual coverage missing manifests {missing_manifests}: {coverage}")
    capture_count = sum(assert_visual_manifest(ROOT / manifest) for manifest in REQUIRED_MANIFESTS)
    if coverage.get("manifestCount", 0) < len(REQUIRED_MANIFESTS):
        raise AssertionError(f"visual coverage manifest count mismatch: {coverage}")
    if coverage.get("minimumCaptureCount", 0) > capture_count:
        raise AssertionError(f"visual coverage minimum capture count exceeds artifacts: {coverage}")
    if coverage.get("actualCaptureCount") != capture_count:
        raise AssertionError(f"visual coverage actual capture count mismatch: expected {capture_count}: {coverage}")

    qa = state.get("qaCoverage") or {}
    if "/qa/visual-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing visual coverage route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_visual_coverage()
        print("visual-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"visual-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
