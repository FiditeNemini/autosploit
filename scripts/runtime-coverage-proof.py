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
    "cache-stats-state-proof.py",
    "live-cache-stats-ui-proof.py",
    "context-window-cache-proof.py",
    "chat-control-actions-proof.py",
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
        if set(coverage.get("supportedFamilies") or []) != {"qwen", "minimax"}:
            raise AssertionError(f"supported family contract mismatch: {coverage}")
        contracts = coverage.get("contracts") or {}
        for key in (
            "modelFolderAutodetect",
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
        if not EXPECTED_PROOFS.issubset(set(coverage.get("proofs") or [])):
            raise AssertionError(f"runtime proof list missing entries: {coverage}")
        if coverage.get("proofCount", 0) < len(EXPECTED_PROOFS):
            raise AssertionError(f"runtime proof count mismatch: {coverage}")
        if not EXPECTED_ROUTES.issubset(set(coverage.get("routes") or [])):
            raise AssertionError(f"runtime route list missing entries: {coverage}")

        live = coverage.get("liveProofs") or {}
        for family in ("qwen", "minimax"):
            item = live.get(family) or {}
            if item.get("metadata") is not True or item.get("repeatCache") is not True:
                raise AssertionError(f"runtime live proof missing {family} metadata/cache checks: {coverage}")

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
