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
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
DEFAULT_MODEL = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP")
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-system-events-settings-toggle.json"


def request_json(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 5.0) -> dict[str, Any]:
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
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
    raise AssertionError(f"app test server did not become ready: {last_error}")


def set_engine_defaults(model: Path, prefix_cache: bool) -> dict[str, Any]:
    return request_json(
        "POST",
        "/qa/apply-app-settings",
        {
            "engine": {
                "modelPath": str(model),
                "useModelGenerationDefaults": True,
                "kvCacheQuantization": "turboquant-q4",
                "prefixCache": prefix_cache,
                "pagedCache": True,
                "blockDiskCache": True,
            }
        },
    )


def press_prefix_cache_checkbox() -> str:
    script = r'''
tell application "ExploitBot" to activate
delay 0.4
tell application "System Events"
  tell process "ExploitBot"
    set elems to entire contents of window 1
    set labelY to -1
    repeat with e in elems
      try
        if role of e as text is "AXStaticText" and name of e as text is "Prefix Cache" then
          set p to position of e
          set labelY to item 2 of p
        end if
      end try
    end repeat
    if labelY is -1 then error "Prefix Cache label not found"

    set bestDelta to 9999
    set bestCheckbox to missing value
    repeat with e in elems
      try
        if role of e as text is "AXCheckBox" then
          set p to position of e
          set delta to (item 2 of p) - labelY
          if delta < 0 then set delta to -delta
          if delta < bestDelta then
            set bestDelta to delta
            set bestCheckbox to e
          end if
        end if
      end try
    end repeat
    if bestCheckbox is missing value then error "Prefix Cache checkbox not found"
    set beforeValue to value of bestCheckbox as text
    perform action "AXPress" of bestCheckbox
    delay 0.3
    set afterValue to value of bestCheckbox as text
    return "prefixCheckbox " & beforeValue & " -> " & afterValue
  end tell
end tell
'''
    return subprocess.check_output(["osascript", "-e", script], text=True, stderr=subprocess.STDOUT).strip()


def press_apply_app_settings() -> str:
    script = r'''
tell application "System Events"
  tell process "ExploitBot"
    set elems to entire contents of window 1
    set bestButton to missing value
    repeat with e in elems
      try
        if role of e as text is "AXButton" then
          set p to position of e
          set s to size of e
          if (item 2 of p) > 880 and (item 1 of s) > 140 and (item 1 of s) < 190 then
            set bestButton to e
            exit repeat
          end if
        end if
      end try
    end repeat
    if bestButton is missing value then error "Apply App Settings button not found"
    perform action "AXPress" of bestButton
    delay 0.5
    return "pressed apply app settings"
  end tell
end tell
'''
    return subprocess.check_output(["osascript", "-e", script], text=True, stderr=subprocess.STDOUT).strip()


def main() -> None:
    output = Path(os.environ.get("EXPLOITBOT_SYSTEM_EVENTS_TOGGLE_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    model = Path(os.environ.get("EXPLOITBOT_SYSTEM_EVENTS_TOGGLE_MODEL", str(DEFAULT_MODEL))).expanduser()
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "system-events-settings-toggle",
        "model": str(model),
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    app: subprocess.Popen[str] | None = None
    app_home = tempfile.TemporaryDirectory(prefix="exploitbot-system-events-toggle-home-")
    error: Exception | None = None
    try:
        if not model.is_dir():
            raise AssertionError(f"model folder missing for settings toggle proof: {model}")

        subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT, check=True)
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["EXPLOITBOT_DATA_DIR"] = str(Path(app_home.name) / ".exploitbot" / "data")
        app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env, text=True)
        wait_for_state()

        set_engine_defaults(model, prefix_cache=True)
        before = request_json("GET", "/state")
        if before.get("engineConfig", {}).get("prefixCache") is not True:
            raise AssertionError(f"prefixCache was not initialized true: {before.get('engineConfig')}")

        request_json("POST", "/qa/window-overlay-action", {"action": "openSettings"})
        request_json("POST", "/qa/settings-category", "cache")
        checkbox_result = press_prefix_cache_checkbox()
        apply_result = press_apply_app_settings()
        after = request_json("GET", "/state")

        if after.get("engineConfig", {}).get("prefixCache") is not False:
            raise AssertionError(f"UI toggle/apply did not change prefixCache to false: {after.get('engineConfig')}")
        if after.get("engineConfig", {}).get("pagedCache") is not True:
            raise AssertionError("pagedCache changed unexpectedly during prefix toggle proof")
        if after.get("engineConfig", {}).get("blockL2Disk") is not True:
            raise AssertionError("blockL2Disk changed unexpectedly during prefix toggle proof")

        report.update(
            {
                "ok": True,
                "checkboxResult": checkbox_result,
                "applyResult": apply_result,
                "beforeEngineConfig": before.get("engineConfig"),
                "afterEngineConfig": after.get("engineConfig"),
                "status": {
                    "nativeUITogglePrefixCache": "PASS",
                    "applyAppSettingsTakesEffect": "PASS",
                    "modelLoaded": "NO",
                    "computerUseMCP": "BLOCKED_SEPARATE_TRANSPORT",
                },
            }
        )
    except Exception as exc:
        error = exc
        report.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        try:
            report["state"] = request_json("GET", "/state", timeout=2.0)
        except Exception:
            pass
    finally:
        try:
            if model.is_dir():
                set_engine_defaults(model, prefix_cache=True)
                report["restoredPrefixCache"] = request_json("GET", "/state", timeout=2.0).get("engineConfig", {}).get("prefixCache")
        except Exception:
            report["restoreError"] = "failed to restore prefixCache"
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
        app_home.cleanup()
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error is not None:
        raise error
    print("system-events-settings-toggle proof passed")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"system-events-settings-toggle proof failed: {exc}", flush=True)
        raise SystemExit(1)
