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
    "streamingUsageMetrics",
    "streamingContentDeltas",
    "streamingReasoningDeltas",
    "streamingToolCallDeltas",
    "responsesEndpointReuse",
    "tokenCounters",
    "reasoningToggle",
    "reasoningCollapse",
    "toolOutputExpansion",
    "approvalControls",
    "sendStopClear",
    "copyAndStashActions",
    "requestAuditBadges",
    "contextInspector",
    "newContextCachePreservation",
    "scrollLockVisuals",
    "toolActionChatControl",
    "stashSendChatControl",
}

REQUIRED_ROUTES = {
    "/send",
    "/stop",
    "/reasoning",
    "/approve",
    "/reject",
    "/context/new",
    "/messages",
    "/qa/seed-chat-visual-states",
    "/qa/chat-visual-mode",
    "/qa/seed-chat-tool-output-expand",
    "/qa/chat-tool-output-expand",
    "/qa/seed-chat-reasoning-collapse",
    "/qa/chat-reasoning-collapse",
    "/qa/seed-chat-actions",
    "/qa/chat-action",
    "/qa/seed-chat-request-audit-visual",
    "/qa/chat-context-inspector",
    "/qa/chat-new-context-confirm",
    "/qa/seed-chat-control-actions",
    "/qa/chat-control-action",
    "/qa/streaming-parser-reuse",
}

REQUIRED_PROOFS = {
    "live-turn-harness.py",
    "chat-actions-proof.py",
    "chat-control-actions-proof.py",
    "chat-turn-controls-proof.py",
    "chat-tool-output-expand-proof.py",
    "chat-reasoning-collapse-proof.py",
    "chat-new-context-confirm-proof.py",
    "context-window-cache-proof.py",
    "request-audit-proof.py",
    "stash-send-chat-control-proof.py",
    "tool-action-chat-control-proof.py",
    "visual-chat-proof.py",
    "visual-chat-interaction-proof.py",
    "visual-context-inspector-proof.py",
    "visual-request-audit-proof.py",
    "streaming-parser-reuse-proof.py",
}

REQUIRED_VISUAL_MANIFESTS = {
    "docs/visual-proofs/checkpoint-71/manifest.json",
    "docs/visual-proofs/checkpoint-72/manifest.json",
    "docs/visual-proofs/checkpoint-84/manifest.json",
    "docs/visual-proofs/checkpoint-87/manifest.json",
}

REQUIRED_STATE_KEYS = {
    "chatActions",
    "chatControlActions",
    "chat",
    "messages",
    "requestContext",
    "contextWindow",
    "qaChatVisual.toolOutputExpansion",
    "qaChatVisual.reasoningBlock",
    "qaChatVisual.newContextConfirm",
    "stashActions",
    "feedRecent",
}

REQUIRED_CACHE_SESSION_FIELDS = [
    "cacheResponsesMethod",
    "cacheResponsesInferenceMethod",
    "sessionBoundaryMode",
    "newModelSessionBehavior",
    "prefixCache",
    "promptL2Disk",
    "pagedCache",
    "blockL2Disk",
    "turboQuantKV",
]

REQUIRED_CACHE_SESSION_FIELD_PROOFS = {
    "cacheResponsesMethod": ["context-window-cache-proof.py", "chat-new-context-confirm-proof.py"],
    "cacheResponsesInferenceMethod": ["context-window-cache-proof.py", "chat-new-context-confirm-proof.py"],
    "sessionBoundaryMode": ["context-window-cache-proof.py", "chat-new-context-confirm-proof.py"],
    "newModelSessionBehavior": ["context-window-cache-proof.py", "chat-new-context-confirm-proof.py"],
    "prefixCache": ["context-window-cache-proof.py", "visual-chat-proof.py"],
    "promptL2Disk": ["context-window-cache-proof.py"],
    "pagedCache": ["context-window-cache-proof.py"],
    "blockL2Disk": ["context-window-cache-proof.py"],
    "turboQuantKV": ["context-window-cache-proof.py", "visual-chat-proof.py"],
}

REQUIRED_HEADER_CACHE_BADGE_PROOFS = {
    "ctx": ["visual-chat-proof.py", "chat-control-actions-proof.py"],
    "cache preserved": ["context-window-cache-proof.py", "visual-chat-proof.py"],
    "prefix/l2/tq": ["context-window-cache-proof.py", "visual-chat-proof.py"],
    "new ctx keeps cache": ["chat-new-context-confirm-proof.py", "visual-chat-proof.py"],
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
        raise AssertionError(f"chat coverage names missing visual manifest: {manifest_path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("ok") is not True:
        raise AssertionError(f"chat coverage visual manifest is not ok: {manifest_path}")
    captures = manifest.get("captures") or []
    if not captures:
        raise AssertionError(f"chat coverage visual manifest has no captures: {manifest_path}")
    missing = [capture for capture in captures if not (ROOT / capture).is_file()]
    if missing:
        raise AssertionError(f"chat coverage visual manifest names missing captures: {missing}")


def assert_chat_coverage() -> None:
    state = request("GET", "/state")
    coverage = request("GET", "/qa/chat-coverage")

    if coverage.get("ok") is not True:
        raise AssertionError(f"/qa/chat-coverage failed: {coverage}")
    if coverage.get("cacheResponseMethod") != "prefix-cache-l2-turboquant":
        raise AssertionError(f"chat coverage cache method mismatch: {coverage}")
    if coverage.get("cacheResponsesInferenceMethod") != "prefix-cache-l2-turboquant":
        raise AssertionError(f"chat coverage cache responses inference method mismatch: {coverage}")
    if coverage.get("newContextBehavior") != "clear-visible-chat-preserve-engine-cache-session":
        raise AssertionError(f"chat coverage new-context behavior mismatch: {coverage}")
    if coverage.get("newModelSessionBehavior") != "new-context-window-preserve-engine-cache-session":
        raise AssertionError(f"chat coverage new model session behavior mismatch: {coverage}")
    expected_header_badges = ["ctx", "cache preserved", "prefix/l2/tq", "new ctx keeps cache"]
    if coverage.get("headerCacheBadges") != expected_header_badges:
        raise AssertionError(f"chat coverage header cache badges mismatch: {coverage}")
    if coverage.get("headerCacheBadgeCount") != len(expected_header_badges):
        raise AssertionError(f"chat coverage header cache badge count mismatch: {coverage}")
    if coverage.get("headerCacheBadgeParity") is not True:
        raise AssertionError(f"chat coverage header cache badge parity mismatch: {coverage}")
    if coverage.get("headerCacheBadgeProofs") != REQUIRED_HEADER_CACHE_BADGE_PROOFS:
        raise AssertionError(f"chat coverage header cache badge proof map mismatch: {coverage}")
    if coverage.get("headerCacheBadgeProofCount") != len(REQUIRED_HEADER_CACHE_BADGE_PROOFS):
        raise AssertionError(f"chat coverage header cache badge proof count mismatch: {coverage}")
    if coverage.get("headerCacheBadgeProofParity") is not True:
        raise AssertionError(f"chat coverage header cache badge proof parity mismatch: {coverage}")
    for badge, proof_names in REQUIRED_HEADER_CACHE_BADGE_PROOFS.items():
        missing_badge_files = sorted(name for name in proof_names if not (ROOT / "scripts" / name).is_file())
        if missing_badge_files:
            raise AssertionError(f"chat header cache badge {badge} names missing proof files {missing_badge_files}: {coverage}")
    if coverage.get("cacheSessionIndicator") != "prefix/l2/tq":
        raise AssertionError(f"chat coverage cache session indicator mismatch: {coverage}")
    if coverage.get("newContextSessionBoundary") != "new ctx keeps cache":
        raise AssertionError(f"chat coverage new context boundary mismatch: {coverage}")
    if coverage.get("cacheSessionFields") != REQUIRED_CACHE_SESSION_FIELDS:
        raise AssertionError(f"chat coverage cache session fields mismatch: {coverage}")
    if coverage.get("cacheSessionFieldCount") != len(REQUIRED_CACHE_SESSION_FIELDS):
        raise AssertionError(f"chat coverage cache session field count mismatch: {coverage}")
    if coverage.get("cacheSessionFieldParity") is not True:
        raise AssertionError(f"chat coverage cache session field parity mismatch: {coverage}")
    if coverage.get("cacheSessionFieldProofs") != REQUIRED_CACHE_SESSION_FIELD_PROOFS:
        raise AssertionError(f"chat coverage cache session field proof map mismatch: {coverage}")
    if coverage.get("cacheSessionFieldProofCount") != len(REQUIRED_CACHE_SESSION_FIELD_PROOFS):
        raise AssertionError(f"chat coverage cache session field proof count mismatch: {coverage}")
    if coverage.get("cacheSessionFieldProofParity") is not True:
        raise AssertionError(f"chat coverage cache session field proof parity mismatch: {coverage}")
    for field, proof_names in REQUIRED_CACHE_SESSION_FIELD_PROOFS.items():
        missing_field_files = sorted(name for name in proof_names if not (ROOT / "scripts" / name).is_file())
        if missing_field_files:
            raise AssertionError(f"chat cache session field {field} names missing proof files {missing_field_files}: {coverage}")

    contracts = coverage.get("contracts") or {}
    missing_contracts = sorted(name for name in REQUIRED_CONTRACTS if contracts.get(name) is not True)
    if missing_contracts:
        raise AssertionError(f"chat coverage missing contracts {missing_contracts}: {coverage}")

    routes = set(coverage.get("routes") or [])
    missing_routes = sorted(REQUIRED_ROUTES.difference(routes))
    if missing_routes:
        raise AssertionError(f"chat coverage missing routes {missing_routes}: {coverage}")

    proofs = set(coverage.get("proofs") or [])
    missing_proofs = sorted(REQUIRED_PROOFS.difference(proofs))
    if missing_proofs:
        raise AssertionError(f"chat coverage missing proofs {missing_proofs}: {coverage}")
    missing_files = sorted(name for name in REQUIRED_PROOFS if not (ROOT / "scripts" / name).is_file())
    if missing_files:
        raise AssertionError(f"chat coverage names non-existent proof files: {missing_files}")
    if coverage.get("proofFileParity") is not True:
        raise AssertionError(f"chat coverage proof file parity mismatch: {coverage}")

    manifests = set(coverage.get("visualManifests") or [])
    missing_manifests = sorted(REQUIRED_VISUAL_MANIFESTS.difference(manifests))
    if missing_manifests:
        raise AssertionError(f"chat coverage missing visual manifests {missing_manifests}: {coverage}")
    for manifest in REQUIRED_VISUAL_MANIFESTS:
        assert_manifest_has_captures(manifest)

    if coverage.get("proofCount", 0) < len(REQUIRED_PROOFS):
        raise AssertionError(f"chat coverage proof count mismatch: {coverage}")
    state_keys = set(coverage.get("stateKeys") or [])
    missing_state_keys = sorted(REQUIRED_STATE_KEYS.difference(state_keys))
    if missing_state_keys:
        raise AssertionError(f"chat coverage missing state keys {missing_state_keys}: {coverage}")

    qa = state.get("qaCoverage") or {}
    if "/qa/chat-coverage" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing chat coverage route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_chat_coverage()
        print("chat-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"chat-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
