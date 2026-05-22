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
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
OUT_DIR = ROOT / "docs" / "visual-proofs" / "checkpoint-101"
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


def live_payload() -> dict:
    data = json.loads(MINIMAX_LIVE_PROOF.read_text(encoding="utf-8"))
    report = data["reports"]["minimax"]
    return {
        "model": report["path"],
        "health": report["health"],
        "cacheStats": report["repeat_cache_stats"],
        "repeatCacheChecks": report["repeat_cache_checks"],
    }


def activate_app() -> None:
    subprocess.run(["osascript", "-e", 'tell application "ExploitBot" to activate'], check=False)
    time.sleep(0.4)


def app_capture_rect() -> str:
    script = '''
tell application "System Events"
  tell process "ExploitBot"
    set frontmost to true
    set p to position of window 1
    set s to size of window 1
    return (item 1 of p as integer) & "," & (item 2 of p as integer) & "," & (item 1 of s as integer) & "," & (item 2 of s as integer)
  end tell
end tell
'''
    raw = subprocess.check_output(["osascript", "-e", script], text=True).strip()
    numbers = re.findall(r"-?\d+", raw)
    if len(numbers) != 4:
        raise AssertionError(f"could not determine ExploitBot window rect: {raw}")
    return ",".join(numbers)


def capture(path: Path) -> None:
    activate_app()
    subprocess.run(["screencapture", "-x", "-R", app_capture_rect(), str(path)], check=True)
    if path.stat().st_size < 50_000:
        raise AssertionError(f"screenshot too small: {path} ({path.stat().st_size} bytes)")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        OUT_DIR.mkdir(parents=True, exist_ok=True)

        seeded = request("POST", "/qa/seed-live-cache-stats", live_payload())
        if seeded.get("ok") is not True:
            raise AssertionError(f"seed failed: {seeded}")
        state = request("GET", "/state")
        stats = state.get("engineCacheStats") or {}
        if state.get("qaSettingsVisual", {}).get("category") != "engine" or stats.get("blockL2Blocks", 0) <= 0:
            raise AssertionError(f"expected live MiniMax cache metrics state: {state}")
        target = OUT_DIR / "settings-live-cache-runtime.png"
        capture(target)
        manifest = {
            "ok": True,
            "captures": [str(target.relative_to(ROOT))],
            "note": "Cropped macOS capture of Settings Engine tab showing real MiniMax live-proof cache metrics parsed from /v1/cache/stats.",
        }
        (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print("visual-live-cache-stats proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError, KeyError) as exc:
        print(f"visual-live-cache-stats proof failed: {exc}", flush=True)
        raise SystemExit(1)
