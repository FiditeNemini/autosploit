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
QWEN_LIVE_PROOF = ROOT / "docs" / "live-proofs" / "checkpoint-76-qwen-repeat-cache-live.json"
MINIMAX_LIVE_PROOF = ROOT / "docs" / "live-proofs" / "checkpoint-80-minimax-strict-live.json"


def request(method: str, path: str, body: object | None = None, timeout: float = 8.0):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8") if not isinstance(body, str) else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
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


def live_payload(path: Path, family: str) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    report = data["reports"][family]
    return {
        "model": report["path"],
        "health": report["health"],
        "cacheStats": report["repeat_cache_stats"],
        "repeatCacheChecks": report["repeat_cache_checks"],
    }


def assert_live_cache_state(*, family: str) -> None:
    state = request("GET", "/state")
    stats = state.get("engineCacheStats")
    if not stats:
        raise AssertionError(f"missing engineCacheStats in /state: {state}")
    if stats.get("turboQuantEnabled") is not True:
        raise AssertionError(f"real cache payload did not set TurboQuant enabled: {stats}")
    if stats.get("turboQuantMakeCache") != "turboquant-q4 encode/decode":
        raise AssertionError(f"real cache payload did not expose TurboQuant encode/decode marker: {stats}")
    if stats.get("prefixCacheHits", 0) <= 0 or stats.get("prefixCacheTokensSaved", 0) <= 0:
        raise AssertionError(f"real cache payload did not expose prefix cache reuse: {stats}")
    if family == "minimax":
        if stats.get("promptL2Entries", 0) <= 0:
            raise AssertionError(f"MiniMax real cache payload did not expose prompt L2 entries: {stats}")
        if stats.get("blockL2Blocks", 0) <= 0:
            raise AssertionError(f"MiniMax real cache payload did not expose block L2 blocks: {stats}")
    if family == "qwen":
        if stats.get("ssmDiskEnabled") is not True or stats.get("ssmDiskEntries", 0) <= 0:
            raise AssertionError(f"Qwen real cache payload did not expose SSM companion disk state: {stats}")
    if stats.get("memoryCacheMB", 0) <= 0:
        raise AssertionError(f"real cache payload did not expose cache memory: {stats}")
    if state.get("qaSettingsVisual", {}).get("category") != "engine":
        raise AssertionError(f"settings engine category was not selected: {state}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        seeded = request("POST", "/qa/seed-live-cache-stats", live_payload(QWEN_LIVE_PROOF, "qwen"))
        if seeded.get("ok") is not True:
            raise AssertionError(f"qwen live cache stats seed failed: {seeded}")
        assert_live_cache_state(family="qwen")

        seeded = request("POST", "/qa/seed-live-cache-stats", live_payload(MINIMAX_LIVE_PROOF, "minimax"))
        if seeded.get("ok") is not True:
            raise AssertionError(f"minimax live cache stats seed failed: {seeded}")
        assert_live_cache_state(family="minimax")
        print("live-cache-stats-ui proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError, KeyError) as exc:
        print(f"live-cache-stats-ui proof failed: {exc}", flush=True)
        raise SystemExit(1)
