#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
OUT_DIR = ROOT / "docs" / "visual-proofs" / "checkpoint-93"


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

        with tempfile.TemporaryDirectory(prefix="exploitbot-unsupported-visual-") as tmp:
            model = Path(tmp) / "Gemma-Unsupported"
            model.mkdir()
            (model / "config.json").write_text(json.dumps({"model_type": "gemma3"}) + "\n", encoding="utf-8")
            (model / "generation_config.json").write_text(json.dumps({"temperature": 0.7}) + "\n", encoding="utf-8")
            request("POST", "/qa/model-folder", str(model))
            request("POST", "/engine/start")
            time.sleep(0.5)
            state = request("GET", "/state")
            if state.get("healthStatus") != "blocked" or "Only Qwen and MiniMax" not in (state.get("engineError") or ""):
                raise AssertionError(f"expected blocked unsupported start state: {state}")

            request("POST", "/qa/settings-category", "engine")
            engine_capture = OUT_DIR / "unsupported-engine-blocked.png"
            capture(engine_capture)

            request("POST", "/qa/settings-category", "model")
            model_capture = OUT_DIR / "unsupported-model-warning.png"
            capture(model_capture)

            manifest = {
                "ok": True,
                "captures": [
                    str(engine_capture.relative_to(ROOT)),
                    str(model_capture.relative_to(ROOT)),
                ],
                "note": "Cropped macOS captures of Settings engine blocked state and model-folder Qwen/MiniMax warning for unsupported folders.",
            }
            (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print("visual-unsupported-model proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"visual-unsupported-model proof failed: {exc}", flush=True)
        raise SystemExit(1)
