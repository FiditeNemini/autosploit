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
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-workflow-panel-state.json"


EXPECTED_TAB_ACTIVITIES = {
    "web": ("done", "search_cve", "Verify Apache CVE evidence"),
    "network": ("running", "run_shell", "tshark capture proof"),
    "creds": ("failed", "hashcat", "hashcat sample hash"),
    "exploit": ("done", "run_shell", "nc -lvnp 4444"),
    "post": ("canceled", "run_shell", "linpeas proof"),
    "osint": ("running", "sherlock", "sherlock qa-user"),
}


def request(method: str, path: str, body: str | dict[str, Any] | None = None, timeout: float = 12.0) -> dict[str, Any]:
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def wait_for_app(timeout: float = 20.0) -> None:
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


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:3000]
        raise AssertionError(message + suffix)


def verify_tab_activities(state: dict[str, Any]) -> dict[str, Any]:
    activities = state.get("tabActivities") or {}
    observed: dict[str, Any] = {}
    for tab, (status, tool, command) in EXPECTED_TAB_ACTIVITIES.items():
        row = activities.get(tab) or {}
        observed[tab] = row
        require(row.get("status") == status, f"{tab} status mismatch", row)
        require(row.get("lastTool") == tool, f"{tab} tool mismatch", row)
        require(row.get("command") == command, f"{tab} command mismatch", row)
        require(int(row.get("count") or 0) >= 1, f"{tab} count did not show activity", row)
    return observed


def verify_lifecycle_rows(state: dict[str, Any]) -> dict[str, Any]:
    lifecycle = {
        "networkLifecycle": state.get("networkLifecycle") or {},
        "credsLifecycle": state.get("credsLifecycle") or {},
        "exploitLifecycle": state.get("exploitLifecycle") or {},
        "postLifecycle": state.get("postLifecycle") or {},
        "osintLifecycle": state.get("osintLifecycle") or {},
    }
    expected_markers = {
        "networkLifecycle": ("capture", "running", "tshark -i en0"),
        "credsLifecycle": ("cracking", "failed", "hashcat qa.hashes"),
        "exploitLifecycle": ("listener", "running", "nc -lvnp 4444"),
        "postLifecycle": ("lateral", "running", "netexec smb"),
        "osintLifecycle": ("username", "running", "sherlock qa-user"),
    }
    for section, (key, status, command) in expected_markers.items():
        row = lifecycle.get(section, {}).get(key) or {}
        require(row.get("status") == status, f"{section}.{key} status mismatch", row)
        require(row.get("command") == command, f"{section}.{key} command mismatch", row)
    return lifecycle


def run() -> None:
    output = Path(os.environ.get("EXPLOITBOT_WORKFLOW_PANEL_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "workflow-panel-state",
        "method": "live app API, no model load, workflow/tab/terminal state",
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=45) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-visual-activity")
        require(seeded.get("ok") is True, "visual activity seed failed", seeded)
        visual_state = request("GET", "/state")
        report["visualSeed"] = {
            "activeTab": visual_state.get("activeTab"),
            "feedRecent": visual_state.get("feedRecent"),
            "tabActivities": verify_tab_activities(visual_state),
            "lifecycle": verify_lifecycle_rows(visual_state),
        }

        switched = request("POST", "/qa/manual-tab-switch", {"tab": "creds"})
        require(switched.get("ok") is True, "manual tab switch failed", switched)
        switched_state = request("GET", "/state")
        report["tabSwitch"] = {
            "activeTab": switched_state.get("activeTab"),
            "tabSwitchActions": switched_state.get("tabSwitchActions"),
        }
        require(switched_state.get("activeTab") == "creds", "active tab did not switch to creds", switched_state.get("activeTab"))

        terminal_seeded = request("POST", "/qa/seed-terminal-tool-visibility")
        require(terminal_seeded.get("ok") is True, "terminal seed failed", terminal_seeded)
        terminal_state = request("GET", "/state")
        terminal = terminal_state.get("terminal") or {}
        active = terminal.get("activeCommand") or {}
        transcripts = terminal.get("commandTranscripts") or []
        transcript_text = json.dumps(transcripts, sort_keys=True)
        report["terminalSeed"] = {
            "activeTab": terminal_state.get("activeTab"),
            "terminal": terminal,
            "feedRecent": terminal_state.get("feedRecent"),
        }
        require(terminal_state.get("activeTab") == "network", "terminal seed did not focus network tab", terminal_state.get("activeTab"))
        require(terminal.get("isVisible") is True, "terminal was not visible", terminal)
        require(active.get("source") == "tabActivities", "terminal active command source mismatch", active)
        require(active.get("tab") == "network", "terminal active command tab mismatch", active)
        require(active.get("command") == "printf qa-terminal-command-output", "terminal active command mismatch", active)
        for marker in ("activityFeed", "rawResults", "tabActivities", "qa-terminal-command-output"):
            require(marker in transcript_text, f"terminal transcript missing {marker}", terminal)

        status = {
            "workflowTabActivities": "PASS",
            "workflowLifecycleRows": "PASS",
            "manualTabSwitch": "PASS",
            "terminalToggleVisible": "PASS",
            "terminalActiveCommand": "PASS",
            "terminalTranscripts": "PASS",
            "noModelLoaded": "PASS" if terminal_state.get("engineRunning") is False else "FAIL",
        }
        report["status"] = status
        if any(value != "PASS" for value in status.values()):
            raise AssertionError(f"workflow panel proof failed status checks: {status}")
        report["ok"] = True
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)

    print(f"workflow panel state proof wrote {output}")


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"workflow panel state proof failed: {exc}", flush=True)
        raise SystemExit(1)
