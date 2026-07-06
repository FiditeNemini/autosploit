#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-app-autonomous-scenario-prepare-route.json"


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def request(method: str, path: str, body: dict[str, Any] | None = None, timeout: float = 20.0) -> Any:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_for_app(timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            request("GET", "/state", timeout=1.0)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"app test server did not become ready: {last_error}")


def build_app_bundle() -> None:
    result = subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError("build_and_run --build-only failed")
    if not APP_BINARY.exists():
        raise RuntimeError(f"app binary missing after build: {APP_BINARY}")


def prepared_message_contains(messages: list[dict[str, Any]], needle: str) -> bool:
    return any(msg.get("role") == "user" and needle in (msg.get("content") or "") for msg in messages)


def run() -> None:
    started = timestamp()
    app: subprocess.Popen[str] | None = None
    try:
        with app_proof_lock("app-autonomous-scenario-prepare-route-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            env = os.environ.copy()
            env["EXPLOITBOT_TESTING"] = "1"
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_for_app()
            web_prepare = request(
                "POST",
                "/qa/autonomous-scenario-prepare",
                {
                    "scenarioId": "webserver_auth_sqli_report_chain",
                    "target": "http://127.0.0.1:18080",
                    "clearFirst": True,
                },
            )
            web_state = request("GET", "/state")
            web_messages = request("GET", "/messages")
            repo_prepare = request(
                "POST",
                "/qa/autonomous-scenario-prepare",
                {
                    "scenarioId": "github_repo_secret_dependency_chain",
                    "target": "/tmp/exploitbot-local-repo-fixture",
                    "clearFirst": True,
                },
            )
            repo_state = request("GET", "/state")
            repo_messages = request("GET", "/messages")

        checks = {
            "webPrepareOk": web_prepare.get("ok") is True,
            "webFinalMarker": "WEBAPP_SQLI_FINAL" in (web_prepare.get("scenarioPrompt") or ""),
            "webRequiredTools": {"httpx", "nuclei", "sqlmap", "search_cve"}.issubset(set(web_prepare.get("requiredTools") or [])),
            "webTab": web_prepare.get("selectedTab") == "web" and web_state.get("activeTab") == "web",
            "webPromptDrafted": prepared_message_contains(web_messages, "webserver_auth_sqli_report_chain"),
            "repoPrepareOk": repo_prepare.get("ok") is True,
            "repoFinalMarker": "GITHUB_REPO_SUPPLY_CHAIN_FINAL" in (repo_prepare.get("scenarioPrompt") or ""),
            "repoRequiredTools": {"trufflehog", "syft", "grype", "osv_scanner"}.issubset(set(repo_prepare.get("requiredTools") or [])),
            "repoTab": repo_prepare.get("selectedTab") == "supplyChain" and repo_state.get("activeTab") == "supplyChain",
            "repoPromptDrafted": prepared_message_contains(repo_messages, "github_repo_secret_dependency_chain"),
            "modeAutopilot": web_state.get("mode") == "autopilot" and repo_state.get("mode") == "autopilot",
            "toolSchemaBudget": (repo_state.get("chat") or {}).get("toolSchemaMaxTools", 0) >= 12,
            "noModelLoaded": not bool(repo_state.get("engineRunning")) and not bool(web_state.get("engineRunning")),
            "isWorking": not bool(repo_state.get("isWorking")) and not bool(web_state.get("isWorking")),
            "sendToChatFalse": web_prepare.get("sendToChat") is False and repo_prepare.get("sendToChat") is False,
        }
        status = {key: "PASS" if value else "FAIL" for key, value in checks.items()}
        ok = all(value == "PASS" for value in status.values())
        report = {
            "ok": ok,
            "proofType": "app-autonomous-scenario-prepare-route-live",
            "proofLevel": "live-debug-app-route-no-model-load",
            "status": "PASS" if ok else "FAIL",
            "startedAt": started,
            "finishedAt": timestamp(),
            "generatedAt": timestamp(),
            "sourceRoute": "/qa/autonomous-scenario-prepare",
            "appApi": APP_API,
            "checks": status,
            "noModelLoaded": status["noModelLoaded"] == "PASS",
            "isWorking": repo_state.get("isWorking"),
            "preparedScenarios": [web_prepare.get("scenarioId"), repo_prepare.get("scenarioId")],
            "webSelectedTab": web_prepare.get("selectedTab"),
            "repoSelectedTab": repo_prepare.get("selectedTab"),
            "webMessageCount": web_state.get("msgs"),
            "repoMessageCount": repo_state.get("msgs"),
            "notes": [
                "Live app route proof only; it prepares scenario prompts and tool-profile state without starting model inference.",
                "Prepared prompts remain scoped to local fixtures and require app tools/evidence/report stages.",
            ],
        }
    finally:
        if app is not None:
            app.terminate()
            try:
                app.wait(timeout=8.0)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=8.0)

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["ok"]:
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(f"app autonomous scenario prepare route proof passed: {ARTIFACT}")


if __name__ == "__main__":
    run()
