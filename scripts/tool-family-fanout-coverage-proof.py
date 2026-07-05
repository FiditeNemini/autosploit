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

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-05-tool-family-fanout-all-tabs.json"


EXPECTED_FAMILIES = {
    "recon": "nmap",
    "web": "nuclei",
    "network": "netexec",
    "creds": "hashcat",
    "exploit": "metasploit",
    "post": "linpeas",
    "supplyChain": "search_cve",
    "osint": "gowitness",
    "report": "search_context",
    "stash": "search_context",
}


def request(method: str, path: str, body: dict | str | None = None, timeout: float = 8.0):
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


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def process_evidence() -> dict:
    output = subprocess.check_output(["ps", "-axo", "pid,rss,comm,args"], text=True)
    app_rows: list[str] = []
    engine_rows: list[str] = []
    engine_tokens = (
        "ExploitBotEngine/launch.py",
        "vmlx_engine.server",
        "mlx_server",
        "Qwen3.6",
        "MiniMax-M",
    )
    for line in output.splitlines():
        parts = line.split(None, 3)
        comm = parts[2] if len(parts) >= 3 else ""
        args = parts[3] if len(parts) >= 4 else ""
        if "ExploitBot.app/Contents/MacOS/ExploitBot" in line:
            app_rows.append(line.strip())
        shell_or_watcher = comm.endswith(("/zsh", "/bash", "/sh")) or "/.claude/" in args
        if not shell_or_watcher and any(token in line for token in engine_tokens):
            engine_rows.append(line.strip())
    return {
        "appRows": app_rows,
        "engineProcessRows": engine_rows,
    }


def write_artifact(coverage: dict, state: dict, messages: list[dict]) -> None:
    families = coverage.get("families") or {}
    status_counts = {
        "PASS": sum(1 for item in families.values() if all(item.get(key) is True for key in ("chatCard", "activityEntry", "tabActivity", "tabResult", "contextCatalog"))),
        "FAIL": len(families) - sum(1 for item in families.values() if all(item.get(key) is True for key in ("chatCard", "activityEntry", "tabActivity", "tabResult", "contextCatalog"))),
    }
    report = {
        "ok": coverage.get("ok") is True and set(families) == set(EXPECTED_FAMILIES),
        "proofType": "tool-family-fanout-all-tabs-live-route",
        "generatedAt": timestamp(),
        "sourceRoute": "/qa/tool-family-fanout-coverage",
        "seedRoute": "/qa/seed-tool-family-fanout-fixture",
        "familyCount": len(families),
        "familyTools": EXPECTED_FAMILIES,
        "families": families,
        "failures": coverage.get("failures") or [],
        "statusCounts": status_counts,
        "messageToolCards": [message.get("tool") for message in messages if message.get("tool")],
        "stateEvidence": {
            "activeTab": state.get("activeTab"),
            "tabActivities": state.get("tabActivities") or {},
            "feedRecent": state.get("feedRecent") or [],
            "healthStatus": state.get("healthStatus"),
            "engineRunning": bool(state.get("engineRunning")),
            "enginePort": state.get("enginePort"),
        },
        "processEvidence": process_evidence(),
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="exploitbot-family-fanout-home-") as home:
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["EXPLOITBOT_SKIP_APP_PROOF_LOCK"] = "1"
        env["HOME"] = home
        env["EXPLOITBOT_DATA_DIR"] = str(Path(home) / ".exploitbot" / "data")
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

        try:
            if app.wait(timeout=30) != 0:
                raise RuntimeError("build_and_run --verify failed")
            wait_for_app()

            seeded = request("POST", "/qa/seed-tool-family-fanout-fixture")
            if seeded.get("ok") is not True:
                raise AssertionError(f"tool family fanout seed failed: {seeded}")

            coverage = request("GET", "/qa/tool-family-fanout-coverage")
            failures = coverage.get("failures") or []
            if failures:
                raise AssertionError(f"tool family fanout coverage failures: {failures}")

            families = coverage.get("families") or {}
            if set(families) != set(EXPECTED_FAMILIES):
                raise AssertionError(f"unexpected family coverage set: {coverage}")
            for family, tool in EXPECTED_FAMILIES.items():
                item = families.get(family) or {}
                if item.get("tool") != tool:
                    raise AssertionError(f"{family} used wrong representative tool: {item}")
                for key in ("chatCard", "activityEntry", "tabActivity", "tabResult", "contextCatalog"):
                    if item.get(key) is not True:
                        raise AssertionError(f"{family} missing {key}: {item}")

            messages = request("GET", "/messages")
            tool_cards = {m.get("tool") for m in messages if m.get("tool")}
            missing_cards = set(EXPECTED_FAMILIES.values()).difference(tool_cards)
            if missing_cards:
                raise AssertionError(f"/messages missing representative tool cards {missing_cards}: {messages}")

            state = request("GET", "/state")
            activities = state.get("tabActivities") or {}
            for family, tool in EXPECTED_FAMILIES.items():
                activity = activities.get(family) or {}
                if activity.get("lastTool") != tool or activity.get("status") != "done":
                    raise AssertionError(f"/state tab activity missing {family}/{tool}: {activity}")
            recent_tools = {entry.get("tool") for entry in state.get("feedRecent", [])}
            if not set(EXPECTED_FAMILIES.values()).issubset(recent_tools):
                raise AssertionError(f"/state.feedRecent missing family tools: {state.get('feedRecent')}")

            write_artifact(coverage, state, messages)
            print(f"tool-family-fanout-coverage proof passed and wrote {ARTIFACT}")
        finally:
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if app.poll() is None:
                app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        with app_proof_lock("tool-family-fanout-coverage-proof.py"):
            run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"tool-family-fanout-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
