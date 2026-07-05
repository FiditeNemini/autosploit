#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
APP = ROOT / "release/ExploitBot.app"
APP_BINARY = APP / "Contents/MacOS/ExploitBot"
MODEL_27B = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP")
RELEASE_READINESS = ROOT / "docs/live-proofs/2026-07-04-release-readiness.json"
NOTARIZATION_PREFLIGHT = ROOT / "docs/live-proofs/2026-07-04-notarization-preflight.json"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-release-visible-smoke.json"
DEFAULT_SCREENSHOT = ROOT / "docs/live-proofs/2026-07-04-release-visible-smoke.png"


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def request_json(method: str, path: str, body: dict[str, Any] | None = None, timeout: float = 8.0) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_for_state(timeout: float = 25.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            return request_json("GET", "/state", timeout=1.0)
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"release app test server did not become ready: {last_error}")


def ax_dump(limit: int = 260) -> str:
    script = f'''
tell application "ExploitBot" to activate
delay 0.5
tell application "System Events"
  tell process "ExploitBot"
    set frontmost to true
    set out to "window=ExploitBot" & linefeed
    set elems to entire contents of window 1
    set out to out & "entireContents=" & (count of elems) & linefeed
    set n to 0
    repeat with e in elems
      set n to n + 1
      if n <= {limit} then
        set roleText to ""
        set nameText to ""
        set valueText to ""
        try
          set roleText to role of e as text
        end try
        try
          set nameText to name of e as text
        end try
        try
          set valueText to value of e as text
        end try
        set out to out & n & " role=" & roleText & " name=" & nameText & " value=" & valueText & linefeed
      end if
    end repeat
    return out
  end tell
end tell
'''
    return subprocess.check_output(["osascript", "-e", script], text=True, stderr=subprocess.STDOUT)


def capture_screenshot(path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(["screencapture", "-x", str(path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.returncode == 0 and path.is_file() and path.stat().st_size > 0


def status_from_evidence(
    *,
    state: dict[str, Any],
    ax_dump: str,
    screenshot_exists: bool,
    release_readiness: dict[str, Any],
    notarization: dict[str, Any],
) -> dict[str, str]:
    visible_window = "window=ExploitBot" in ax_dump or "AXWindow" in ax_dump
    main_workspace = "Ready to pentest" in ax_dump and "Give me a target and scope" in ax_dump
    api_state = bool(state)
    no_model_loaded = state.get("engineRunning") is False
    local_package = release_readiness.get("localPackageStatus") == "PASS"
    distribution_ready = (
        release_readiness.get("distributionStatus") == "PASS"
        and notarization.get("distributionStatus") == "PASS"
    )
    local_display = all((local_package, api_state, visible_window, main_workspace, screenshot_exists, no_model_loaded))
    return {
        "releaseAppArtifact": "PASS" if local_package else "FAIL",
        "apiStateAvailable": "PASS" if api_state else "FAIL",
        "visibleWindow": "PASS" if visible_window else "FAIL",
        "mainWorkspaceVisible": "PASS" if main_workspace else "FAIL",
        "screenshotCaptured": "PASS" if screenshot_exists else "FAIL",
        "localDisplayStatus": "PASS" if local_display else "FAIL",
        "distributionStatus": "PASS" if distribution_ready else "BLOCKED",
        "noModelLoaded": "PASS" if no_model_loaded else "FAIL",
    }


def stop_app(proc: subprocess.Popen[str] | None = None) -> None:
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if proc is not None and proc.poll() is None:
        proc.send_signal(signal.SIGTERM)


def main() -> None:
    output = Path(os.environ.get("EXPLOITBOT_RELEASE_VISIBLE_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    screenshot = Path(os.environ.get("EXPLOITBOT_RELEASE_VISIBLE_SCREENSHOT", str(DEFAULT_SCREENSHOT))).expanduser()
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "release-visible-smoke",
        "proofLevel": "release-app-live-api-system-events-window-and-screenshot",
        "startedAt": timestamp(),
        "releaseApp": str(APP.relative_to(ROOT)),
        "screenshot": str(screenshot.relative_to(ROOT)),
    }
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-release-visible-home-")
    proc: subprocess.Popen[str] | None = None
    error: Exception | None = None
    try:
        if not APP_BINARY.is_file():
            raise AssertionError(f"release app binary missing: {APP_BINARY}")
        release_readiness = json.loads(RELEASE_READINESS.read_text(encoding="utf-8"))
        notarization = json.loads(NOTARIZATION_PREFLIGHT.read_text(encoding="utf-8"))

        stop_app()
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = temp_home.name
        env["EXPLOITBOT_DATA_DIR"] = str(Path(temp_home.name) / ".exploitbot" / "data")
        proc = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env, text=True)
        before = wait_for_state()
        model_path = str(MODEL_27B) if MODEL_27B.is_dir() else ""
        onboarded = request_json("POST", "/qa/onboarding-complete", {
            "language": "en",
            "modelPath": model_path,
            "opName": "Release Visible Smoke",
            "mode": "autopilot",
            "scope": "127.0.0.1/32",
            "startEngine": False,
        })
        if onboarded.get("ok") is not True:
            raise AssertionError(f"release app onboarding route failed: {onboarded}")
        state = request_json("GET", "/state")
        dump = ax_dump()
        screenshot_exists = capture_screenshot(screenshot)
        status = status_from_evidence(
            state=state,
            ax_dump=dump,
            screenshot_exists=screenshot_exists,
            release_readiness=release_readiness,
            notarization=notarization,
        )
        report.update({
            "ok": status["localDisplayStatus"] == "PASS",
            "before": {
                "engineRunning": before.get("engineRunning"),
                "showOnboarding": (before.get("modeSelection") or {}).get("showOnboarding"),
            },
            "state": {
                "engineRunning": state.get("engineRunning"),
                "showOnboarding": (state.get("modeSelection") or {}).get("showOnboarding"),
                "activeOpName": (state.get("modeSelection") or {}).get("activeOpName"),
                "modelPath": (state.get("engineConfig") or {}).get("modelPath"),
            },
            "status": status,
            "releaseReadiness": {
                "generatedAt": release_readiness.get("generatedAt"),
                "localPackageStatus": release_readiness.get("localPackageStatus"),
                "distributionStatus": release_readiness.get("distributionStatus"),
            },
            "notarization": {
                "generatedAt": notarization.get("generatedAt"),
                "distributionStatus": notarization.get("distributionStatus"),
                "nextAction": notarization.get("nextAction"),
            },
            "axTail": dump[-5000:],
        })
        if report["ok"] is not True:
            raise AssertionError(f"release visible smoke failed: {status}")
    except Exception as exc:
        error = exc
        report.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        report["finishedAt"] = timestamp()
        report["generatedAt"] = report["finishedAt"]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        stop_app(proc)
        temp_home.cleanup()

    if error is not None:
        raise error
    print(f"release visible smoke proof wrote {output}")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"release visible smoke proof failed: {exc}", flush=True)
        raise SystemExit(1)
