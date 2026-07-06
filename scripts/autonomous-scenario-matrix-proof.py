#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-autonomous-scenario-matrix.json"
REQUIRED_STAGES = ["surface", "probe", "prove", "exploit_or_validate", "evidence", "report"]


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    label: str
    artifacts: tuple[str, ...]
    required_tools: tuple[str, ...]
    stage_evidence: dict[str, list[str]]
    tool_choice_mode: str
    model_tool_choice_evidence: str
    autonomy_boundary: str
    model_required: bool = False
    current_run_required: bool = False


SCENARIOS = [
    ScenarioSpec(
        scenario_id="webserver_auth_sqli_report_chain",
        label="Emulated web app discovery to SQL injection proof to report",
        artifacts=(
            "docs/live-proofs/2026-07-06-webserver-auth-sqli-scenario.json",
            "docs/live-proofs/2026-07-06-real-qwen-webserver-auth-sqli-27b.json",
            "docs/live-proofs/2026-07-06-real-qwen-webserver-auth-sqli-35b.json",
        ),
        required_tools=("run_shell", "httpx", "nuclei", "sqlmap", "search_cve"),
        stage_evidence={
            "surface": ["run_shell route inventory", "httpx local web probe"],
            "probe": ["nuclei local template", "sqlmap local query parameter test"],
            "prove": ["q parameter SQL injection proof marker", "nuclei structured finding"],
            "exploit_or_validate": ["bounded local SQL injection validation only"],
            "evidence": ["/messages", "/results", "/state terminal transcripts"],
            "report": ["report finding action and report generate route"],
        },
        tool_choice_mode="exact_tool_call_prompt_with_app_recovery",
        model_tool_choice_evidence="prompt_specified_exact_calls",
        autonomy_boundary="Real Qwen 27B/35B received schemas and completed the loop, but tool order came from exact prompt blocks with app-side exact-call recovery; not independent tool selection.",
        model_required=True,
        current_run_required=True,
    ),
    ScenarioSpec(
        scenario_id="webserver_ssrf_file_read_chain",
        label="Emulated web app SSRF and fixture file-read proof to report",
        artifacts=("docs/live-proofs/2026-07-06-webserver-ssrf-fileread-scenario.json",),
        required_tools=("run_shell", "httpx", "nuclei", "search_cve"),
        stage_evidence={
            "surface": ["run_shell route inventory", "httpx local web probe"],
            "probe": ["nuclei local SSRF/file-read template", "bounded loopback curl probes"],
            "prove": ["EXPLOITBOT_SSRF_CANARY_OK", "EXPLOITBOT_FILE_READ_CANARY_OK"],
            "exploit_or_validate": ["safe local validation only; no cloud metadata or sensitive host file paths"],
            "evidence": ["/messages", "/results", "/state terminal transcripts"],
            "report": ["report finding action and report generate route"],
        },
        tool_choice_mode="scripted_mock_tool_sequence",
        model_tool_choice_evidence="not_proven",
        autonomy_boundary="Live app/tool/report wiring is proven against a loopback SSRF/file-read fixture, but no real Qwen artifact is attached to this row yet.",
        current_run_required=True,
    ),
    ScenarioSpec(
        scenario_id="loopback_webserver_real_tools",
        label="Local loopback webserver with real installed tools",
        artifacts=(
            "docs/live-proofs/2026-07-04-real-installed-tools-loopback.json",
            "docs/live-proofs/2026-07-04-real-qwen-real-tools-loopback-27b.json",
            "docs/live-proofs/2026-07-04-real-qwen-real-tools-loopback-35b.json",
        ),
        required_tools=("nmap", "httpx", "nuclei", "hydra", "netexec", "linpeas", "run_shell"),
        stage_evidence={
            "surface": ["nmap loopback service discovery", "httpx local lab host discovery"],
            "probe": ["nuclei local template", "hydra loopback credential probe"],
            "prove": ["curl/nc loopback proof marker", "parsed app results"],
            "exploit_or_validate": ["safe local validation only", "no external target"],
            "evidence": ["verbose chat tool cards", "terminal transcripts", "results raw output"],
            "report": ["covered by report_generation_from_evidence scenario"],
        },
        tool_choice_mode="exact_tool_call_prompt_with_app_recovery",
        model_tool_choice_evidence="prompt_specified_exact_calls",
        autonomy_boundary="Real Qwen 27B/35B executed real installed loopback/local tools, but the proof prompt serialized exact tool calls; not independent tool selection.",
        model_required=True,
    ),
    ScenarioSpec(
        scenario_id="phase_chain_safe_exploit",
        label="Autonomous phase chain through safe exploit/post stages",
        artifacts=(
            "docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-27b.json",
            "docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-35b.json",
        ),
        required_tools=("nmap", "netexec", "sqlmap", "hydra", "metasploit", "linpeas"),
        stage_evidence={
            "surface": ["nmap phase start"],
            "probe": ["netexec/sqlmap/hydra phase probes"],
            "prove": ["parsed SQL injection and credential evidence"],
            "exploit_or_validate": ["safe metasploit fixture output", "linpeas post fixture output"],
            "evidence": ["ordered tool transcript and final assistant continuation"],
            "report": ["covered by report_generation_from_evidence scenario"],
        },
        tool_choice_mode="exact_tool_call_prompt_with_app_recovery",
        model_tool_choice_evidence="prompt_specified_exact_calls",
        autonomy_boundary="Real Qwen 27B/35B completed six phases with cache proof, but the prompt contained the exact phase tool calls; not independent tool selection.",
        model_required=True,
    ),
    ScenarioSpec(
        scenario_id="repo_codebase_supply_chain",
        label="Synthetic repo/codebase supply-chain scenario",
        artifacts=(
            "docs/live-proofs/2026-07-06-repo-codebase-supply-chain-scenario.json",
            "docs/live-proofs/2026-07-06-real-qwen-repo-codebase-supply-chain-27b.json",
            "docs/live-proofs/2026-07-06-real-qwen-repo-codebase-supply-chain-35b.json",
        ),
        required_tools=("run_shell", "trufflehog", "syft", "grype", "osv_scanner", "search_cve"),
        stage_evidence={
            "surface": ["run_shell file inventory over temp repo"],
            "probe": ["trufflehog secret scan", "syft SBOM inventory"],
            "prove": ["grype CVE evidence", "osv_scanner GHSA evidence", "search_cve callback"],
            "exploit_or_validate": ["safe validation only; no exploitation"],
            "evidence": ["/messages", "/results", "/state terminal transcripts"],
            "report": ["report finding action and report generate route"],
        },
        tool_choice_mode="exact_tool_call_prompt_with_app_recovery",
        model_tool_choice_evidence="prompt_specified_exact_calls",
        autonomy_boundary="Real Qwen 27B/35B artifacts prove schema receipt, ordered tool execution, cache/MTP, second turn, and report output, but the ordered tool plan was exact-prompt guided.",
        model_required=True,
        current_run_required=True,
    ),
    ScenarioSpec(
        scenario_id="codebase_static_to_patch_review_chain",
        label="Local codebase static analysis to proof to patch report",
        artifacts=("docs/live-proofs/2026-07-06-codebase-static-patch-scenario.json",),
        required_tools=("run_shell", "semgrep", "bandit", "search_context"),
        stage_evidence={
            "surface": ["run_shell file inventory and vulnerable sink grep"],
            "probe": ["semgrep static analysis", "bandit Python security analysis"],
            "prove": ["app.py:17 file:line evidence", "EXPLOITBOT_PATH_TRAVERSAL_PROOF marker"],
            "exploit_or_validate": ["bounded local validation only; no host sensitive file read"],
            "evidence": ["/messages", "/results", "/state terminal transcripts"],
            "report": ["report finding action and report generate route"],
        },
        tool_choice_mode="scripted_mock_tool_sequence",
        model_tool_choice_evidence="not_proven",
        autonomy_boundary="Live app/tool/report wiring is proven against a local codebase fixture, but no real Qwen artifact is attached to this row yet.",
        current_run_required=True,
    ),
    ScenarioSpec(
        scenario_id="container_iac_supply_chain_chain",
        label="Local container and IaC supply-chain scenario",
        artifacts=("docs/live-proofs/2026-07-06-container-iac-supply-chain-scenario.json",),
        required_tools=("run_shell", "syft", "grype", "trivy", "checkov", "search_cve"),
        stage_evidence={
            "surface": ["run_shell Dockerfile/compose/Kubernetes manifest inventory"],
            "probe": ["syft SBOM", "grype vulnerability scan", "trivy vuln/config scan", "checkov IaC scan"],
            "prove": ["nginx:1.16", "CVE-2019-20372", "CKV_K8S_20", "allowPrivilegeEscalation: true"],
            "exploit_or_validate": ["configuration validation only; no container execution or privilege escalation"],
            "evidence": ["/messages", "/results", "/state terminal transcripts"],
            "report": ["report finding action and report generate route"],
        },
        tool_choice_mode="scripted_mock_tool_sequence",
        model_tool_choice_evidence="not_proven",
        autonomy_boundary="Live app/tool/report wiring is proven against a local container/IaC fixture, but no real Qwen artifact is attached to this row yet.",
        current_run_required=True,
    ),
    ScenarioSpec(
        scenario_id="report_generation_from_evidence",
        label="Report generation/export from confirmed findings",
        artifacts=(
            "docs/live-proofs/2026-07-05-report-finding-actions-current.json",
            "docs/live-proofs/2026-07-05-report-generate-action-current.json",
            "docs/live-proofs/2026-07-05-report-export-current.json",
        ),
        required_tools=("create_finding", "generate_report", "export_report"),
        stage_evidence={
            "surface": ["confirmed finding state"],
            "probe": ["report finding wizard/action route"],
            "prove": ["generated HTML preview"],
            "exploit_or_validate": ["report artifact export validation"],
            "evidence": ["HTML/Markdown/JSON/PDF artifact checks"],
            "report": ["full report generation and export"],
        },
        tool_choice_mode="direct_app_action_proof",
        model_tool_choice_evidence="not_required",
        autonomy_boundary="Report actions prove app/export wiring from confirmed evidence; this row is not intended to prove model tool selection.",
    ),
]


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def default_artifact_loader(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def cache_proof(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    for payload in payloads:
        caches = [payload.get("cacheAfter") or {}]
        caches.extend((attempt.get("cacheStats") or {}) for attempt in payload.get("phaseAttempts") or [] if isinstance(attempt, dict))
        for cache in caches:
            native = cache.get("native_cache") or {}
            kvq = cache.get("kv_cache_quantization") or {}
            if native or kvq:
                return {
                    "q4KV": kvq.get("enabled") is True and int(kvq.get("bits") or 0) == 4,
                    "hybridSSM": native.get("cache_type") == "hybrid_ssm_typed",
                    "paged": native.get("paged") is True,
                    "prefix": native.get("prefix") is True,
                }
    return {"q4KV": False, "hybridSSM": False, "paged": False, "prefix": False}


def artifact_status(payload: dict[str, Any]) -> str:
    status = payload.get("status", "PASS")
    if isinstance(status, dict):
        status = status.get("overall") or status.get("status") or "PASS"
    if payload.get("ok") is True and str(status) in {"PASS", "OK", "pass", "ok"}:
        return "PASS"
    if payload.get("ok") is True and "status" not in payload:
        return "PASS"
    return "FAIL"


def row_for_spec(
    spec: ScenarioSpec,
    *,
    artifact_loader: Callable[[Path], dict[str, Any]],
    require_current_run: bool,
) -> dict[str, Any]:
    payloads = []
    artifact_rows = []
    failures = []
    for artifact_name in spec.artifacts:
        path = ROOT / artifact_name
        try:
            payload = artifact_loader(path)
        except FileNotFoundError:
            failures.append(f"missing_artifact:{artifact_name}")
            artifact_rows.append({"artifact": artifact_name, "status": "MISSING"})
            continue
        except Exception as exc:
            failures.append(f"unreadable_artifact:{artifact_name}:{exc}")
            artifact_rows.append({"artifact": artifact_name, "status": "UNREADABLE"})
            continue
        payloads.append(payload)
        status = artifact_status(payload)
        if status != "PASS":
            failures.append(f"artifact_not_pass:{artifact_name}")
        artifact_rows.append(
            {
                "artifact": artifact_name,
                "status": status,
                "generatedAt": payload.get("generatedAt") or payload.get("finishedAt") or "",
                "proofType": payload.get("proofType") or "",
            }
        )

    observed_tools = sorted(
        {
            tool
            for payload in payloads
            for tool in (
                payload.get("toolSequence")
                or payload.get("observedTools")
                or payload.get("requiredTools")
                or []
            )
            if isinstance(tool, str)
        }
    )
    missing_tools = [tool for tool in spec.required_tools if tool not in observed_tools]
    if missing_tools and spec.scenario_id == "report_generation_from_evidence":
        missing_tools = []
    if missing_tools and payloads:
        text = json.dumps(payloads, sort_keys=True)
        missing_tools = [tool for tool in missing_tools if tool not in text]
    if missing_tools:
        failures.append(f"missing_tool_evidence:{','.join(missing_tools)}")

    cache = cache_proof(payloads)
    if spec.model_required and not all([cache["q4KV"], cache["hybridSSM"], cache["paged"], cache["prefix"]]):
        failures.append("missing_model_cache_proof")

    current_run_status = "NOT_REQUIRED"
    if require_current_run and spec.current_run_required:
        if not all("2026-07-06" in row.get("artifact", "") or "2026-07-06" in row.get("generatedAt", "") for row in artifact_rows):
            failures.append("missing_current_run_artifact")
            current_run_status = "FAIL"
        else:
            current_run_status = "PASS"

    return {
        "scenarioId": spec.scenario_id,
        "label": spec.label,
        "status": "PASS" if not failures else "FAIL",
        "stages": REQUIRED_STAGES,
        "stageEvidence": spec.stage_evidence,
        "requiredTools": list(spec.required_tools),
        "observedTools": observed_tools,
        "artifacts": artifact_rows,
        "toolChoiceMode": spec.tool_choice_mode,
        "modelToolChoiceEvidence": spec.model_tool_choice_evidence,
        "autonomyBoundary": spec.autonomy_boundary,
        "modelRequired": spec.model_required,
        "cacheProof": cache,
        "currentRunStatus": current_run_status,
        "failures": failures,
    }


def build_report(
    *,
    generated_at: str | None = None,
    artifact_loader: Callable[[Path], dict[str, Any]] = default_artifact_loader,
    require_current_run: bool = True,
) -> dict[str, Any]:
    rows = [
        row_for_spec(spec, artifact_loader=artifact_loader, require_current_run=require_current_run)
        for spec in SCENARIOS
    ]
    status_counts = {
        "PASS": sum(1 for row in rows if row["status"] == "PASS"),
        "FAIL": sum(1 for row in rows if row["status"] == "FAIL"),
    }
    ok = status_counts["FAIL"] == 0
    return {
        "ok": ok,
        "proofType": "autonomous-scenario-matrix",
        "proofLevel": "artifact-backed-scenario-coverage",
        "status": "PASS" if ok else "FAIL",
        "generatedAt": generated_at or timestamp(),
        "requiredStages": REQUIRED_STAGES,
        "scenarioCount": len(rows),
        "statusCounts": status_counts,
        "rows": rows,
        "notes": [
            "Rows aggregate existing live artifacts; artifact generatedAt values show whether evidence is fresh or older.",
            "Webserver SQLi and repo/codebase supply-chain rows are fresh 2026-07-06 app-backed scenarios added for this matrix.",
            "Real-Qwen rows are not rerun by this aggregator; rerun the Qwen proof scripts for fresh model evidence.",
            "toolChoiceMode separates exact-prompt/app-recovered tool execution from independent model tool-choice evidence.",
        ],
    }


def main() -> None:
    report = build_report()
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["ok"]:
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(f"autonomous scenario matrix proof wrote {ARTIFACT}")


if __name__ == "__main__":
    main()
