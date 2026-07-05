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

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-terminal-tool-visibility.json"


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
    env["EXPLOITBOT_SKIP_APP_PROOF_LOCK"] = "1"
    output = Path(os.environ.get("EXPLOITBOT_TERMINAL_VISIBILITY_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    report = {
        "ok": False,
        "proofType": "terminal-tool-visibility",
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "appApi": APP_API,
    }
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-terminal-tool-visibility")
        report["seeded"] = seeded
        if seeded.get("ok") is not True:
            raise AssertionError(f"terminal visibility seed failed: {seeded}")

        state = request("GET", "/state")
        terminal = state.get("terminal") or {}
        report["terminal"] = terminal
        if terminal.get("surfaceContract") != "terminal-visibility-command-transcripts":
            raise AssertionError(f"terminal surface contract missing: {terminal}")
        if terminal.get("isVisible") is not True:
            raise AssertionError(f"terminal visibility not reflected in state: {terminal}")

        transcripts = terminal.get("commandTranscripts") or []
        transcript_text = json.dumps(transcripts, sort_keys=True)
        for marker in ("activityFeed", "rawResults", "tabActivities", "run_shell", "printf qa-terminal-command-output", "qa-terminal-command-output"):
            if marker not in transcript_text:
                raise AssertionError(f"terminal transcript missing {marker!r}: {terminal}")

        active = terminal.get("activeCommand") or {}
        if active.get("source") != "tabActivities" or active.get("tool") != "run_shell":
            raise AssertionError(f"terminal active command did not reflect running tab command: {active}")
        if active.get("command") != "printf qa-terminal-command-output":
            raise AssertionError(f"terminal active command missing command text: {active}")

        feed_text = "\n".join(entry.get("text", "") for entry in state.get("feedRecent", []))
        report["feedRecent"] = state.get("feedRecent", [])
        if "Running run_shell" not in feed_text or "$ printf qa-terminal-command-output" not in feed_text:
            raise AssertionError(f"feedRecent missing terminal command evidence: {state.get('feedRecent')}")

        report["ok"] = True
        report["status"] = {
            "terminalVisible": "PASS",
            "commandTranscripts": "PASS",
            "activeCommand": "PASS",
            "feedCommandEvidence": "PASS",
        }
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"terminal-tool-visibility proof passed; wrote {output}")
    except Exception as exc:
        report["error"] = str(exc)
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        raise
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        with app_proof_lock("terminal-tool-visibility-proof.py"):
            run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"terminal-tool-visibility proof failed: {exc}", flush=True)
        raise SystemExit(1)
