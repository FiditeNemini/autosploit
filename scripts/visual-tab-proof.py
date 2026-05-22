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
OUT_DIR = ROOT / "docs" / "visual-proofs" / "checkpoint-69"


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
    rect = ",".join(numbers)
    if rect.count(",") != 3:
        raise AssertionError(f"could not determine ExploitBot window rect: {rect}")
    return rect


def capture(path: Path) -> None:
    activate_app()
    subprocess.run(["screencapture", "-x", "-R", app_capture_rect(), str(path)], check=True)
    if path.stat().st_size < 50_000:
        raise AssertionError(f"screenshot too small: {path} ({path.stat().st_size} bytes)")
    info = subprocess.check_output(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)], text=True)
    if "pixelWidth" not in info or "pixelHeight" not in info:
        raise AssertionError(f"missing image dimensions for {path}: {info}")


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
        seeded = request("POST", "/qa/seed-visual-activity")
        if seeded.get("ok") is not True:
            raise AssertionError(f"visual activity seed failed: {seeded}")

        captures = []
        for tab in ["web", "network", "creds", "exploit", "post", "osint"]:
            request("POST", "/tab", tab)
            state = request("GET", "/state")
            if state.get("activeTab") != tab:
                raise AssertionError(f"active tab did not switch to {tab}: {state}")
            target = OUT_DIR / f"{tab}-activity.png"
            capture(target)
            captures.append(str(target.relative_to(ROOT)))

        manifest = {
            "ok": True,
            "captures": captures,
            "note": "Cropped macOS captures of the ExploitBot window. QA state seeds tab bar activity plus lifecycle lanes before each tab capture.",
        }
        (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print("visual-tab proof passed")
        print(json.dumps(manifest, indent=2))
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"visual-tab proof failed: {exc}", flush=True)
        raise SystemExit(1)
