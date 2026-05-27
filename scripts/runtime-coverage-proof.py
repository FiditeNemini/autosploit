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

EXPECTED_PROOFS = {
    "engine-no-model-metadata-proof.py",
    "model-folder-warning-proof.py",
    "unsupported-model-start-proof.py",
    "qwen-multimodal-start-proof.py",
    "cache-stats-state-proof.py",
    "live-cache-stats-ui-proof.py",
    "context-window-cache-proof.py",
    "chat-control-actions-proof.py",
    "engine-python-runtime-resolution-proof.py",
    "release-app-live-qwen-proof.py",
    "release-app-qwen-cross-restart-cache-proof.py",
    "release-app-live-minimax-proof.py",
    "zaya-visual-live-proof.py",
    "verify-live-models.py",
    "prove-block-l2-cache.py",
    "prove-ssm-rederive-status.py",
}

EXPECTED_ROUTES = {
    "/qa/model-folder",
    "/engine/start",
    "/context/new",
    "/qa/seed-settings-visual-state",
    "/qa/seed-live-cache-stats",
    "/qa/engine-python-runtime",
}

EXPECTED_LIVE_ARTIFACTS = {
    "minimaxRestartReplay": ("docs/live-proofs/checkpoint-110-minimax-restart-replay-live.json", "minimax"),
    "minimaxBlockL2Replay": ("docs/live-proofs/checkpoint-111-minimax-block-l2-restart-replay-live.json", "minimax"),
    "qwenHybridBlockL2SSMReplay": ("docs/live-proofs/checkpoint-112-qwen-hybrid-block-l2-ssm-restart-replay-live.json", "qwen"),
    "releaseAppQwenCrossRestartCache": ("docs/live-proofs/checkpoint-463-release-app-qwen-cross-restart-cache.json", "qwen-release-app"),
    "qwenHybridFullPrefixSkip": ("docs/live-proofs/checkpoint-113-qwen-hybrid-full-prefix-skip-live.json", "qwen"),
    "minimaxNoThinking": ("docs/live-proofs/checkpoint-114-minimax-no-thinking-live.json", "minimax"),
    "qwenHybridCataloguePrefixShape": ("docs/live-proofs/checkpoint-115-qwen-hybrid-catalogue-prefix-shape-live.json", "qwen"),
}

EXPECTED_CACHE_COMPONENTS = [
    "prefixCache",
    "promptL2Disk",
    "pagedKVCache",
    "blockL2Disk",
    "turboQuantKV",
    "ssmCompanionL2",
    "newContextPreservesEngineSession",
]

EXPECTED_CACHE_COMPONENT_PROOFS = {
    "prefixCache": ["verify-live-models.py", "context-window-cache-proof.py"],
    "promptL2Disk": ["engine-no-model-metadata-proof.py", "prove-block-l2-cache.py"],
    "pagedKVCache": ["engine-no-model-metadata-proof.py", "verify-live-models.py"],
    "blockL2Disk": ["prove-block-l2-cache.py", "live-cache-stats-ui-proof.py"],
    "turboQuantKV": ["engine-no-model-metadata-proof.py", "cache-stats-state-proof.py"],
    "ssmCompanionL2": ["prove-ssm-rederive-status.py", "live-cache-stats-ui-proof.py", "release-app-live-qwen-proof.py", "release-app-qwen-cross-restart-cache-proof.py"],
    "newContextPreservesEngineSession": ["context-window-cache-proof.py", "chat-control-actions-proof.py"],
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

        coverage = request("GET", "/qa/runtime-coverage")
        if coverage.get("ok") is not True:
            raise AssertionError(f"runtime coverage route failed: {coverage}")
        if set(coverage.get("supportedFamilies") or []) != {"qwen", "minimax", "zaya"}:
            raise AssertionError(f"supported family contract mismatch: {coverage}")
        contracts = coverage.get("contracts") or {}
        for key in (
            "modelFolderAutodetect",
            "enginePythonRuntimePreflight",
            "generationDefaults",
            "reasoningParserAuto",
            "toolParserAuto",
            "prefixCacheRequired",
            "cacheResponseMethod",
            "turboQuantKV",
            "promptL2",
            "blockL2",
            "pagedCache",
            "ssmCompanionL2",
            "newContextPreservesEngineSession",
            "unsupportedStartBlocked",
        ):
            if contracts.get(key) is not True:
                raise AssertionError(f"runtime contract missing {key}: {coverage}")
        if coverage.get("cacheResponseMethod") != "prefix-cache-l2-turboquant":
            raise AssertionError(f"wrong cache response method: {coverage}")
        if coverage.get("cacheResponsesInferenceMethod") != "prefix-cache-l2-turboquant":
            raise AssertionError(f"wrong cache responses inference method: {coverage}")
        if coverage.get("newModelSessionBehavior") != "new-context-window-preserve-engine-cache-session":
            raise AssertionError(f"wrong new model session behavior: {coverage}")
        if coverage.get("cacheComponents") != EXPECTED_CACHE_COMPONENTS:
            raise AssertionError(f"runtime cache component list mismatch: {coverage}")
        if coverage.get("cacheComponentCount") != len(EXPECTED_CACHE_COMPONENTS):
            raise AssertionError(f"runtime cache component count mismatch: {coverage}")
        if coverage.get("cacheComponentParity") is not True:
            raise AssertionError(f"runtime cache component parity mismatch: {coverage}")
        if coverage.get("cacheComponentProofs") != EXPECTED_CACHE_COMPONENT_PROOFS:
            raise AssertionError(f"runtime cache component proof map mismatch: {coverage}")
        if coverage.get("cacheComponentProofCount") != len(EXPECTED_CACHE_COMPONENT_PROOFS):
            raise AssertionError(f"runtime cache component proof count mismatch: {coverage}")
        if coverage.get("cacheComponentProofParity") is not True:
            raise AssertionError(f"runtime cache component proof parity mismatch: {coverage}")
        for component, proof_names in EXPECTED_CACHE_COMPONENT_PROOFS.items():
            missing_component_files = sorted(name for name in proof_names if not (ROOT / "scripts" / name).is_file())
            if missing_component_files:
                raise AssertionError(f"runtime cache component {component} names missing proof files {missing_component_files}: {coverage}")
        if coverage.get("cacheComponentProofFileParity") is not True:
            raise AssertionError(f"runtime cache component proof-file parity mismatch: {coverage}")
        if not EXPECTED_PROOFS.issubset(set(coverage.get("proofs") or [])):
            raise AssertionError(f"runtime proof list missing entries: {coverage}")
        if coverage.get("proofCount", 0) < len(EXPECTED_PROOFS):
            raise AssertionError(f"runtime proof count mismatch: {coverage}")
        missing_files = sorted(name for name in EXPECTED_PROOFS if not (ROOT / "scripts" / name).is_file())
        if missing_files:
            raise AssertionError(f"runtime coverage names non-existent proof files: {missing_files}")
        if coverage.get("proofFileParity") is not True:
            raise AssertionError(f"runtime proof file parity mismatch: {coverage}")
        if not EXPECTED_ROUTES.issubset(set(coverage.get("routes") or [])):
            raise AssertionError(f"runtime route list missing entries: {coverage}")

        live = coverage.get("liveProofs") or {}
        for family in ("qwen", "minimax"):
            item = live.get(family) or {}
            if item.get("metadata") is not True or item.get("repeatCache") is not True:
                raise AssertionError(f"runtime live proof missing {family} metadata/cache checks: {coverage}")
        qwen_live = live.get("qwen") or {}
        if qwen_live.get("ssmReDerive") is not True:
            raise AssertionError(f"runtime live proof missing qwen SSM rederive check: {coverage}")
        artifacts = coverage.get("liveProofArtifacts") or {}
        if coverage.get("liveProofArtifactCount") != len(EXPECTED_LIVE_ARTIFACTS):
            raise AssertionError(f"runtime live artifact count mismatch: {coverage}")
        if coverage.get("liveProofArtifactFileParity") is not True:
            raise AssertionError(f"runtime live artifact file parity mismatch: {coverage}")
        for name, (path, family) in EXPECTED_LIVE_ARTIFACTS.items():
            if artifacts.get(name) != path:
                raise AssertionError(f"runtime live artifact {name} mismatch: {coverage}")
            artifact_path = ROOT / path
            if not artifact_path.is_file():
                raise AssertionError(f"runtime live artifact missing on disk: {path}")
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            if payload.get("ok") is not True:
                raise AssertionError(f"runtime live artifact not ok: {path} {payload}")
            if family == "qwen-release-app":
                replay = payload.get("replay") or {}
                summary = replay.get("cacheSummary") or {}
                if replay.get("cachedTokens", 0) <= 0:
                    raise AssertionError(f"release-app Qwen replay missing cached tokens: {path} {payload}")
                if summary.get("blockL2DiskHits", 0) <= 0 or summary.get("ssmDiskHits", 0) <= 0:
                    raise AssertionError(f"release-app Qwen replay missing block/SSM L2 hit: {path} {payload}")
                if summary.get("ssmReDeriveRequested", 0) != 0 or summary.get("ssmReDeriveFailed", 0) != 0:
                    raise AssertionError(f"release-app Qwen replay used/faulted SSM rederive: {path} {payload}")
                continue
            if family not in (payload.get("reports") or {}):
                raise AssertionError(f"runtime live artifact missing {family} report: {path} {payload}")
        qwen_rederive_artifact = ROOT / EXPECTED_LIVE_ARTIFACTS["qwenHybridBlockL2SSMReplay"][0]
        qwen_payload = json.loads(qwen_rederive_artifact.read_text(encoding="utf-8"))
        qwen_report = (qwen_payload.get("reports") or {}).get("qwen") or {}
        ssm_checks = qwen_report.get("ssm_rederive_checks") or {}
        if coverage.get("qwenSSMReDeriveArtifact") != EXPECTED_LIVE_ARTIFACTS["qwenHybridBlockL2SSMReplay"][0]:
            raise AssertionError(f"runtime qwen SSM rederive artifact path mismatch: {coverage}")
        if coverage.get("qwenSSMReDeriveRequested") != ssm_checks.get("requested"):
            raise AssertionError(f"runtime qwen SSM rederive requested mismatch: {coverage}")
        if coverage.get("qwenSSMReDeriveCompleted") != ssm_checks.get("completed"):
            raise AssertionError(f"runtime qwen SSM rederive completed mismatch: {coverage}")
        if coverage.get("qwenSSMReDeriveNoFailures") != ssm_checks.get("no_failures"):
            raise AssertionError(f"runtime qwen SSM rederive no-failures mismatch: {coverage}")
        if coverage.get("qwenSSMReDeriveLastNumTokens") != ssm_checks.get("last_num_tokens"):
            raise AssertionError(f"runtime qwen SSM rederive token count mismatch: {coverage}")
        if coverage.get("qwenSSMReDeriveArtifactOK") is not True:
            raise AssertionError(f"runtime qwen SSM rederive artifact check missing: {coverage}")

        print("runtime-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"runtime-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
