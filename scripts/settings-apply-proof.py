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
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
MOCK_ENGINE = "http://127.0.0.1:18991"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-settings-apply-state.json"


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def passfail(value: bool) -> str:
    return "PASS" if value else "FAIL"


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


def build_app_bundle() -> None:
    result = subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError("build_and_run --build-only failed")
    if not APP_BINARY.exists():
        raise RuntimeError(f"app binary missing after build: {APP_BINARY}")


def write_report(report: dict) -> None:
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_report(started_at: str, finished_at: str, before: dict, after: dict, budget: dict) -> dict:
    checks = {
        "engineNotRestarted": passfail(
            after["engineRunning"] == before["engineRunning"]
            and after["healthStatus"] == before["healthStatus"]
            and after["model"] == before["model"]
        ),
        "chatLoopSettingsApplied": passfail(
            after["chat"]["maxIterations"] == 7
            and after["chat"]["toolSchemaMaxTools"] == 13
            and after["chat"]["includeUnavailableToolSchemas"] is True
            and after["chat"]["forceFinalAnswerAfterToolResults"] is False
            and after["chat"]["enableReasoning"] is False
        ),
        "runtimeGenerationMirrored": passfail(
            after["engineConfig"]["useModelGenerationDefaults"] is False
            and after["engineConfig"]["temperature"] == 0.0
            and after["engineConfig"]["topP"] == 1.0
            and after["engineConfig"]["maxTokens"] == 64
            and budget["maxTokens"] == 64
            and budget["chatMaxTokens"] == 64
            and budget["contracts"]["maxTokensForwarded"] is True
        ),
        "contextSettingsApplied": passfail(
            after["contextCatalog"]["enabled"] is True
            and after["contextCatalog"]["maxSnippets"] == 3
            and after["contextCatalog"]["includeAssets"] is False
            and after["contextCatalog"]["includeRecentToolOutput"] is False
            and after["contextCatalog"]["includeFindings"] is True
            and after["contextCatalog"]["includeStash"] is True
            and after["contextCatalog"]["cveMode"] == "current"
        ),
        "agentSettingsApplied": passfail(
            after["agents"]["multiAgentEnabled"] is True
            and after["agents"]["maxConcurrentAgents"] == 8
        ),
    }
    ok = all(value == "PASS" for value in checks.values())
    return {
        "ok": ok,
        "status": "PASS" if ok else "FAIL",
        "proofType": "settings-apply-state-live",
        "proofLevel": "live-app-test-server-no-engine-restart",
        "startedAt": started_at,
        "finishedAt": finished_at,
        "generatedAt": finished_at,
        "checks": checks,
        "stateEvidenceBefore": before,
        "stateEvidenceAfter": after,
        "contextBudgetEvidence": budget,
        "notes": [
            "This proof launches the real Swift app in EXPLOITBOT_TESTING mode with a temporary HOME.",
            "It proves /qa/apply-app-settings mutates app/chat/context/agent/generation state without starting or restarting the model engine.",
            "It does not prove a real Qwen model request after toggling settings; that remains a separate heavy live boundary.",
        ],
    }


def run() -> None:
    started_at = timestamp()
    app: subprocess.Popen[str] | None = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-settings-apply-home-", ignore_cleanup_errors=True)
    report: dict = {"ok": False, "status": "FAIL", "proofType": "settings-apply-state-live", "startedAt": started_at}
    error: Exception | None = None
    try:
        home = Path(temp_home.name)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")

        with app_proof_lock("settings-apply-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_for_app()

            request("POST", "/engine/mock", MOCK_ENGINE)
            before = request("GET", "/state")
            request("POST", "/qa/apply-app-settings", {
                "maxIterations": 7,
                "toolSchemaMaxTools": 13,
                "includeUnavailableToolSchemas": True,
                "forceFinalAnswerAfterToolResults": False,
                "chat": {"enableReasoning": False},
                "engine": {
                    "useModelGenerationDefaults": False,
                    "temperature": 0.0,
                    "topP": 1.0,
                    "maxTokens": 64,
                },
                "context": {
                    "enabled": True,
                    "maxSnippets": 3,
                    "includeAssets": False,
                    "includeFindings": True,
                    "includeRecentToolOutput": False,
                    "includeStash": True,
                    "cveMode": "current",
                },
                "agents": {
                    "multiAgentEnabled": True,
                    "maxConcurrentAgents": 8,
                },
            })
            after = request("GET", "/state")
            budget = request("GET", "/qa/context-budget-compaction")

            report = build_report(started_at, timestamp(), before, after, budget)
            if not report["ok"]:
                raise AssertionError("settings apply checks failed", report["checks"])

        print(f"settings-apply proof passed: {ARTIFACT}")
    except Exception as exc:
        error = exc
        report.update({"ok": False, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}", "finishedAt": timestamp()})
        try:
            report["stateEvidenceAfterFailure"] = request("GET", "/state", timeout=5.0)
        except Exception:
            pass
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
        temp_home.cleanup()
        write_report(report)

    if error is not None:
        raise error


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"settings-apply proof failed: {exc}", flush=True)
        raise SystemExit(1)
