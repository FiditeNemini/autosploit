#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-app-autonomous-scenario-fixture-session-prepare.json"
FIXTURE_PROOF = ROOT / "scripts/autonomous-scenario-fixture-setup-proof.py"

SCENARIO_IDS = [
    "webserver_auth_sqli_report_chain",
    "webserver_ssrf_file_read_chain",
    "github_repo_secret_dependency_chain",
    "codebase_static_to_patch_review_chain",
    "container_iac_supply_chain_chain",
    "network_service_credential_post_chain",
]
EXPECTED_TABS = {
    "webserver_auth_sqli_report_chain": "web",
    "webserver_ssrf_file_read_chain": "web",
    "github_repo_secret_dependency_chain": "supplyChain",
    "codebase_static_to_patch_review_chain": "supplyChain",
    "container_iac_supply_chain_chain": "supplyChain",
    "network_service_credential_post_chain": "network",
}


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def load_fixture_module():
    spec = importlib.util.spec_from_file_location("exploitbot_autonomous_fixture_setup", FIXTURE_PROOF)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


def service_alive(module: Any, scenario_id: str, target: str) -> bool:
    if scenario_id == "webserver_auth_sqli_report_chain":
        return (
            "EXPLOITBOT_WEBAPP_LAB_OK" in module.read_url(f"{target}/")
            and "EXPLOITBOT_SQLI_PROOF_USER=alice" in module.read_url(f"{target}/search?q=1%27%20OR%201%3D1--")
        )
    if scenario_id == "webserver_ssrf_file_read_chain":
        return (
            "EXPLOITBOT_SSRF_CANARY_OK" in module.read_url(f"{target}/canary")
            and "EXPLOITBOT_FILE_READ_CANARY_OK" in module.read_url(f"{target}/download?path=fixture-note.txt")
        )
    if scenario_id == "network_service_credential_post_chain":
        return (
            "ExploitBot demo service" in module.read_url(f"{target}/banner")
            and "EXPLOITBOT_NETWORK_LOGIN_OK" in module.read_url(f"{target}/login?user=demo&pass=demo")
            and "EXPLOITBOT_LINPEAS_FIXTURE_OK" in module.read_url(f"{target}/post-check")
        )
    path = Path(target)
    if scenario_id == "github_repo_secret_dependency_chain":
        return (
            (path / ".git").is_dir()
            and module.file_contains(path / ".env.example", "EXPLOITBOT_FAKE_TOKEN_DO_NOT_USE")
            and module.file_contains(path / "VULNERABILITIES.md", "CVE-2021-23337")
        )
    if scenario_id == "codebase_static_to_patch_review_chain":
        return (path / "app.py").is_file() and module.file_contains(path / "app.py", "EXPLOITBOT_PATH_TRAVERSAL_PROOF")
    if scenario_id == "container_iac_supply_chain_chain":
        return (
            module.file_contains(path / "Dockerfile", "EXPLOITBOT_CONTAINER_IAC_PROOF")
            and module.file_contains(path / "k8s" / "deployment.yaml", "allowPrivilegeEscalation: true")
        )
    return False


def run() -> None:
    started = timestamp()
    app: subprocess.Popen[str] | None = None
    fixture_session = None
    module = load_fixture_module()
    prepared_rows: list[dict[str, Any]] = []
    state: dict[str, Any] = {}
    try:
        with app_proof_lock("app-autonomous-scenario-fixture-session-prepare-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            fixture_session = module.build_fixture_session()
            env = os.environ.copy()
            env["EXPLOITBOT_TESTING"] = "1"
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_for_app()
            for scenario_id in SCENARIO_IDS:
                target = fixture_session.target_for(scenario_id)
                alive_before = service_alive(module, scenario_id, target)
                prepare = request(
                    "POST",
                    "/qa/autonomous-scenario-prepare",
                    {"scenarioId": scenario_id, "target": target, "clearFirst": True},
                )
                state = request("GET", "/state")
                messages = request("GET", "/messages")
                prompt = prepare.get("scenarioPrompt") or ""
                prepared_rows.append(
                    {
                        "scenarioId": scenario_id,
                        "target": target,
                        "selectedTab": prepare.get("selectedTab"),
                        "expectedTab": EXPECTED_TABS[scenario_id],
                        "checks": {
                            "prepareOk": "PASS" if prepare.get("ok") is True else "FAIL",
                            "targetInPrompt": "PASS" if target in prompt else "FAIL",
                            "scenarioInPrompt": "PASS" if scenario_id in prompt else "FAIL",
                            "fixtureSetupInPrompt": "PASS" if "Fixture setup:" in prompt else "FAIL",
                            "fixtureSetupInResponse": "PASS" if isinstance(prepare.get("fixtureSetup"), dict) else "FAIL",
                            "promptDrafted": "PASS" if prepared_message_contains(messages, target) else "FAIL",
                            "tabSelected": "PASS" if prepare.get("selectedTab") == EXPECTED_TABS[scenario_id] else "FAIL",
                            "sendToChatFalse": "PASS" if prepare.get("sendToChat") is False else "FAIL",
                            "servicesAliveDuringPrepare": "PASS" if alive_before and service_alive(module, scenario_id, target) else "FAIL",
                        },
                    }
                )

        aggregate_checks = {
            "allScenariosPrepared": len(prepared_rows) == len(SCENARIO_IDS),
            "allPromptsContainLiveTargets": all(row["checks"]["targetInPrompt"] == "PASS" for row in prepared_rows),
            "servicesAliveDuringPrepare": all(row["checks"]["servicesAliveDuringPrepare"] == "PASS" for row in prepared_rows),
            "tabsSelected": all(row["checks"]["tabSelected"] == "PASS" for row in prepared_rows),
            "noModelLoaded": not bool(state.get("engineRunning")) and not bool(state.get("loadedModel")),
            "isWorkingFalse": not bool(state.get("isWorking")),
        }
        checks = {key: "PASS" if value else "FAIL" for key, value in aggregate_checks.items()}
        ok = all(value == "PASS" for value in checks.values()) and all(
            all(status == "PASS" for status in row["checks"].values()) for row in prepared_rows
        )
        report = {
            "ok": ok,
            "proofType": "app-autonomous-scenario-fixture-session-prepare-live",
            "proofLevel": "live-debug-app-route-all-scenarios-no-model-load",
            "status": "PASS" if ok else "FAIL",
            "startedAt": started,
            "finishedAt": timestamp(),
            "generatedAt": timestamp(),
            "sourceRoute": "/qa/autonomous-scenario-prepare",
            "fixtureSource": "scripts/autonomous-scenario-fixture-setup-proof.py::build_fixture_session",
            "scenarioCount": len(prepared_rows),
            "checks": checks,
            "preparedRows": prepared_rows,
            "noModelLoaded": checks["noModelLoaded"] == "PASS",
            "serverLifecycle": "loopback services stay alive through all prepare calls and are stopped before artifact write",
            "notes": [
                "No model inference is started by this proof.",
                "This proof bridges fixture materialization to app prompt preparation for all autonomous scenarios.",
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
        if fixture_session is not None:
            fixture_session.close()

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["ok"]:
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(f"app autonomous scenario fixture session prepare proof passed: {ARTIFACT}")


if __name__ == "__main__":
    run()
