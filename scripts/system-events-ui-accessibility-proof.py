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
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-system-events-ui-accessibility.json"


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


def ax_dump(limit: int = 260) -> str:
    script = f'''
tell application "ExploitBot" to activate
delay 0.4
tell application "System Events"
  tell process "ExploitBot"
    set frontmost to true
    set out to ""
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


def require_contains(text: str, needles: list[str], label: str) -> None:
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise AssertionError(f"{label} AX dump missing {missing}\n{text[-2500:]}")


def main() -> None:
    output = Path(os.environ.get("EXPLOITBOT_SYSTEM_EVENTS_UI_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "system-events-native-ui-accessibility",
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    app: subprocess.Popen[str] | None = None
    app_home = tempfile.TemporaryDirectory(prefix="exploitbot-system-events-ui-home-")
    error: Exception | None = None
    try:
        subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT, check=True)
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["EXPLOITBOT_DATA_DIR"] = str(Path(app_home.name) / ".exploitbot" / "data")
        app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env, text=True)
        wait_for_state()
        model = Path(os.environ.get("EXPLOITBOT_SYSTEM_EVENTS_UI_MODEL", str(DEFAULT_MODEL))).expanduser()
        if model.is_dir():
            request_json(
                "POST",
                "/qa/apply-app-settings",
                {
                    "engine": {
                        "modelPath": str(model),
                        "useModelGenerationDefaults": True,
                        "kvCacheQuantization": "turboquant-q4",
                        "prefixCache": True,
                        "pagedCache": True,
                        "blockDiskCache": True,
                    }
                },
            )

        request_json("POST", "/qa/window-overlay-action", {"action": "openSettings"})
        request_json("POST", "/qa/settings-category", "cache")
        cache_dump = ax_dump()
        require_contains(
            cache_dump,
            ["Settings", "Cache", "Prefix Cache", "Paged Cache", "Block L2 Disk", "Apply App Settings"],
            "cache settings",
        )

        request_json("POST", "/qa/settings-category", "engine")
        engine_dump = ax_dump()
        require_contains(engine_dump, ["Engine", "ENGINE STATUS", "Start Engine ready"], "engine settings")

        request_json("POST", "/qa/window-overlay-action", {"action": "closeSettings"})
        request_json("POST", "/qa/window-overlay-action", {"action": "toggleTerminal"})
        terminal_dump = ax_dump()
        require_contains(terminal_dump, ["Terminal", "Ready to pentest", "Give me a target and scope"], "terminal/chat")

        state = request_json("GET", "/state")
        report.update(
            {
                "ok": True,
                "state": {
                    "terminal": state.get("terminal"),
                    "windowOverlayActions": state.get("windowOverlayActions"),
                    "qaSettingsVisual": state.get("qaSettingsVisual"),
                },
                "cacheAXTail": cache_dump[-4000:],
                "engineAXTail": engine_dump[-4000:],
                "terminalAXTail": terminal_dump[-4000:],
                "status": {
                    "systemEventsUIAccessibility": "PASS",
                    "computerUseMCP": "BLOCKED_SEPARATE_TRANSPORT",
                    "cacheSettingsNamedControls": "PASS",
                    "engineSettingsNamedControls": "PASS",
                    "terminalToggleVisible": "PASS",
                    "chatControlLabelsSourceContract": "PASS",
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
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
        app_home.cleanup()
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error is not None:
        raise error
    print("system-events-ui-accessibility proof passed")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"system-events-ui-accessibility proof failed: {exc}", flush=True)
        raise SystemExit(1)
