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
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-app-autonomous-scenario-catalog-route.json"

REQUIRED_STAGES = ["surface", "probe", "prove", "exploit_or_validate", "evidence", "report"]
REQUIRED_SCENARIOS = {
    "webserver_auth_sqli_report_chain",
    "webserver_ssrf_file_read_chain",
    "github_repo_secret_dependency_chain",
    "codebase_static_to_patch_review_chain",
    "container_iac_supply_chain_chain",
    "network_service_credential_post_chain",
}
REQUIRED_ROUTE_TOOLS = {
    "webserver_auth_sqli_report_chain": {"httpx", "nuclei", "sqlmap", "search_cve", "create_finding", "generate_report"},
    "github_repo_secret_dependency_chain": {"trufflehog", "syft", "grype", "osv_scanner", "search_cve"},
    "network_service_credential_post_chain": {"nmap", "httpx", "hydra", "netexec", "linpeas"},
}


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def request(method: str, path: str, timeout: float = 20.0) -> Any:
    req = urllib.request.Request(f"{APP_API}{path}", method=method)
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


def validate_catalog(route_payload: dict[str, Any]) -> dict[str, Any]:
    scenarios = route_payload.get("scenarios") or []
    by_id = {row.get("scenarioId"): row for row in scenarios if isinstance(row, dict)}
    missing_scenarios = sorted(REQUIRED_SCENARIOS - set(by_id))
    scenario_failures: dict[str, list[str]] = {}
    for scenario_id in REQUIRED_SCENARIOS & set(by_id):
        row = by_id[scenario_id]
        failures: list[str] = []
        stage_plan = row.get("stagePlan") or {}
        tools = set(row.get("requiredTools") or [])
        if row.get("status") != "READY_TO_RUN":
            failures.append("status_not_ready")
        if row.get("safetyBoundary") != "local_fixture_only":
            failures.append("safety_boundary_not_local_fixture_only")
        if not row.get("finalMarker"):
            failures.append("missing_final_marker")
        missing_stages = [stage for stage in REQUIRED_STAGES if stage not in stage_plan]
        if missing_stages:
            failures.append("missing_stages:" + ",".join(missing_stages))
        missing_tools = sorted(REQUIRED_ROUTE_TOOLS.get(scenario_id, set()) - tools)
        if missing_tools:
            failures.append("missing_tools:" + ",".join(missing_tools))
        if failures:
            scenario_failures[scenario_id] = failures

    checks = {
        "routeOk": route_payload.get("ok") is True,
        "proofType": route_payload.get("proofType") == "autonomous-scenario-catalog",
        "executionBoundary": route_payload.get("executionBoundary") == "local-emulated-targets-only",
        "requiredStages": route_payload.get("requiredStages") == REQUIRED_STAGES,
        "scenarioCount": route_payload.get("scenarioCount") == len(REQUIRED_SCENARIOS),
        "allRequiredScenariosPresent": not missing_scenarios,
        "allScenarioContractsReady": not scenario_failures,
    }
    return {
        "checks": {key: "PASS" if value else "FAIL" for key, value in checks.items()},
        "missingScenarios": missing_scenarios,
        "scenarioFailures": scenario_failures,
        "routeScenarioCount": route_payload.get("scenarioCount"),
        "routeScenarioIds": sorted(by_id),
    }


def run() -> None:
    started = timestamp()
    app: subprocess.Popen[str] | None = None
    try:
        with app_proof_lock("app-autonomous-scenario-catalog-route-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            env = os.environ.copy()
            env["EXPLOITBOT_TESTING"] = "1"
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_for_app()
            route_payload = request("GET", "/qa/autonomous-scenario-catalog", timeout=20.0)
            state = request("GET", "/state", timeout=20.0)

        validation = validate_catalog(route_payload)
        no_model_loaded = not bool(state.get("engineRunning")) and not bool(state.get("loadedModel"))
        checks = dict(validation["checks"])
        checks["noModelLoaded"] = "PASS" if no_model_loaded else "FAIL"
        ok = all(value == "PASS" for value in checks.values())
        report = {
            "ok": ok,
            "proofType": "app-autonomous-scenario-catalog-route-live",
            "proofLevel": "live-debug-app-route-no-model-load",
            "status": "PASS" if ok else "FAIL",
            "startedAt": started,
            "finishedAt": timestamp(),
            "generatedAt": timestamp(),
            "sourceRoute": "/qa/autonomous-scenario-catalog",
            "appApi": APP_API,
            "noModelLoaded": no_model_loaded,
            "checks": checks,
            "routeScenarioCount": validation["routeScenarioCount"],
            "routeScenarioIds": validation["routeScenarioIds"],
            "missingScenarios": validation["missingScenarios"],
            "scenarioFailures": validation["scenarioFailures"],
            "executionBoundary": route_payload.get("executionBoundary"),
            "requiredStages": route_payload.get("requiredStages"),
            "notes": [
                "Live app route proof only; this does not load a model.",
                "The route exposes local_fixture_only scenarios for model-driving harnesses and UI QA.",
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
    print(f"app autonomous scenario catalog route proof passed: {ARTIFACT}")


if __name__ == "__main__":
    run()
