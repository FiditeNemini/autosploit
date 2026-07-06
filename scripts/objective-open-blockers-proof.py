#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/live-proofs/2026-07-04-pass-partial-blocked-matrix.json"
GOAL_AUDIT = ROOT / "docs/live-proofs/2026-07-04-goal-requirement-audit.json"
NOTARIZATION_PREFLIGHT = ROOT / "docs/live-proofs/2026-07-04-notarization-preflight.json"
RELEASE_PUBLIC_TRUTH = ROOT / "docs/live-proofs/2026-07-05-release-public-truth.json"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-05-objective-open-blockers-current.json"


FULL_CONTEXT_AREA = "Full-context-length stress"
RELEASE_AREA = "Release/distribution readiness"
INDEPENDENT_TOOL_CHOICE_AREA = "Independent natural-language scenario tool selection"


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:4000]
        raise AssertionError(message + suffix)


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), "required proof artifact is missing", str(path.relative_to(ROOT)))
    return json.loads(path.read_text(encoding="utf-8"))


def validate_evidence_paths(rows: list[dict[str, Any]]) -> list[str]:
    missing = []
    for row in rows:
        for evidence in row.get("evidence") or []:
            if not (ROOT / evidence).exists():
                missing.append(evidence)
    return sorted(set(missing))


def status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {status: sum(1 for row in rows if row.get("status") == status) for status in ("PASS", "PARTIAL", "BLOCKED")}


def open_blocker_areas(rows: list[dict[str, Any]]) -> set[str]:
    return {row.get("area") for row in rows if row.get("status") in {"PARTIAL", "BLOCKED"}}


def aggregate_overall_status(rows: list[dict[str, Any]]) -> str:
    statuses = {row.get("status") for row in rows}
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if "PARTIAL" in statuses:
        return "PARTIAL"
    return "PASS"


def build_full_context_row(row: dict[str, Any], goal_row: dict[str, Any]) -> dict[str, Any]:
    evidence = sorted(set((row.get("evidence") or []) + (goal_row.get("evidence") or [])))
    return {
        "area": row["area"],
        "status": row["status"],
        "requirementId": goal_row["id"],
        "blockingCondition": "near_max_final_output_and_cache_write_missing",
        "safeCeilingTokens": 192000,
        "missingEvidence": (
            "192k live Qwen completion is proven with final assistant output and post-generation "
            "cache write evidence. The explicit 196k above-ceiling retry reached chunked prefill "
            "but stalled without final output/cache writes, and true near-max final assistant output "
            "plus post-generation cache write proof above that ceiling is still missing."
        ),
        "requiredNextEvidence": (
            "Run an explicit high-risk long-context target above the 192k proven safe ceiling with "
            "fresh memory headroom, then capture final assistant output plus post-generation q4 "
            "TurboQuant KV, paged/prefix, block-L2, and SSM companion cache writes."
        ),
        "evidence": evidence,
        "notes": row.get("notes", ""),
    }


def build_release_row(
    row: dict[str, Any],
    goal_row: dict[str, Any],
    notarization: dict[str, Any],
    public_truth: dict[str, Any],
) -> dict[str, Any]:
    evidence = sorted(set((row.get("evidence") or []) + (goal_row.get("evidence") or [])))
    for path in (NOTARIZATION_PREFLIGHT, RELEASE_PUBLIC_TRUTH):
        rel = str(path.relative_to(ROOT))
        if rel not in evidence:
            evidence.append(rel)
    return {
        "area": row["area"],
        "status": row["status"],
        "requirementId": goal_row["id"],
        "blockingCondition": "notarization_credentials_and_stapled_tickets_missing",
        "missingEvidence": (
            "No accepted notary credential input/default keychain profile is configured, Gatekeeper "
            "rejects the app without notarization context, and app/DMG stapled tickets are missing."
        ),
        "requiredNextEvidence": [
            "Configure notary credentials without exposing secrets.",
            "Run package/notarize flow.",
            "Validate stapled app and DMG tickets.",
            "Pass Gatekeeper assessment.",
            "Publish release assets whose hashes match the current local manifest.",
        ],
        "releaseNextAction": notarization.get("nextAction"),
        "publicTruthNextAction": public_truth.get("nextAction"),
        "evidence": sorted(set(evidence)),
        "notes": row.get("notes", ""),
    }


def build_independent_tool_choice_row(row: dict[str, Any], requirement: dict[str, Any]) -> dict[str, Any]:
    return {
        "area": INDEPENDENT_TOOL_CHOICE_AREA,
        "status": row.get("status"),
        "requirementId": "independent_model_tool_choice",
        "blockingCondition": "independent_model_tool_choice_not_proven",
        "missingEvidence": requirement.get("missingEvidence") or (
            "A real Qwen 27B/35B natural-language objective proof must show the model choosing the surface/probe/prove/report tool order without exact tool-call blocks."
        ),
        "evidence": row.get("evidence") or [],
        "requiredNextEvidence": [
            "Run a local-fixture webserver/repo/codebase scenario with a natural-language objective only.",
            "no exact tool-call blocks",
            "Provide allowed tool schemas but no exact tool-call blocks or forced function-specific retry.",
            "Prove the model-selected ordered tool chain, verbose transcripts, final answer, and cache/MTP evidence for 27B and 35B.",
        ],
    }


def build_report_from_payloads(
    matrix: dict[str, Any],
    goal_audit: dict[str, Any],
    notarization: dict[str, Any],
    public_truth: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    require(matrix.get("proofType") == "pass-partial-blocked-matrix", "unexpected matrix proof type", matrix)
    require(goal_audit.get("proofType") == "goal-requirement-audit", "unexpected goal audit proof type", goal_audit)
    require(notarization.get("proofType") == "notarization-preflight", "unexpected notarization proof type", notarization)
    require(public_truth.get("proofType") == "release-public-truth", "unexpected public release proof type", public_truth)
    require(isinstance(goal_audit.get("objectiveComplete"), bool), "goal audit objectiveComplete must be boolean", goal_audit)
    require(isinstance(goal_audit.get("completionClaimAllowed"), bool), "goal audit completionClaimAllowed must be boolean", goal_audit)

    rows = matrix.get("rows") or []
    counts = status_counts(rows)
    require(matrix.get("statusCounts") == counts, "matrix statusCounts do not match rows", {
        "stored": matrix.get("statusCounts"),
        "computed": counts,
    })
    require(matrix.get("rowCount") == 27, "unexpected matrix row count", matrix.get("rowCount"))
    missing_evidence = validate_evidence_paths(rows)
    require(not missing_evidence, "matrix has missing evidence paths", missing_evidence)

    by_area = {row.get("area"): row for row in rows}
    goal_by_id = {row.get("id"): row for row in goal_audit.get("rows") or []}
    full_context = by_area[FULL_CONTEXT_AREA]
    independent_tool_choice = by_area[INDEPENDENT_TOOL_CHOICE_AREA]
    release = by_area[RELEASE_AREA]
    require(full_context.get("status") in {"PASS", "PARTIAL"}, "full-context row status drifted", full_context)
    require(independent_tool_choice.get("status") in {"PASS", "PARTIAL"}, "independent tool-choice row status drifted", independent_tool_choice)
    require(release.get("status") in {"PASS", "BLOCKED"}, "release row status drifted", release)

    expected_open_areas: set[str] = set()
    if full_context.get("status") == "PARTIAL":
        expected_open_areas.add(FULL_CONTEXT_AREA)
    if independent_tool_choice.get("status") == "PARTIAL":
        expected_open_areas.add(INDEPENDENT_TOOL_CHOICE_AREA)
    if release.get("status") == "BLOCKED":
        expected_open_areas.add(RELEASE_AREA)
    actual_open_areas = open_blocker_areas(rows)
    require(actual_open_areas == expected_open_areas, "unexpected open matrix rows", {
        "expected": sorted(expected_open_areas),
        "actual": sorted(actual_open_areas),
    })

    report_rows = []
    if full_context.get("status") == "PARTIAL":
        report_rows.append(build_full_context_row(full_context, goal_by_id["generation_reasoning_context"]))
    if independent_tool_choice.get("status") == "PARTIAL":
        report_rows.append(build_independent_tool_choice_row(independent_tool_choice, goal_by_id["independent_model_tool_choice"]))
    if release.get("status") == "BLOCKED":
        report_rows.append(build_release_row(release, goal_by_id["release_displayable"], notarization, public_truth))

    report_missing_evidence = validate_evidence_paths(report_rows)
    require(not report_missing_evidence, "open blockers report has missing evidence paths", report_missing_evidence)
    overall_status = aggregate_overall_status(rows)
    objective_complete = (
        overall_status == "PASS"
        and not report_rows
        and goal_audit.get("overallStatus") == "PASS"
        and goal_audit.get("objectiveComplete") is True
        and goal_audit.get("completionClaimAllowed") is True
    )

    return {
        "ok": True,
        "proofType": "objective-open-blockers",
        "proofLevel": "matrix-and-goal-audit-derived-no-model-load",
        "generatedAt": generated_at or time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sourceMatrix": str(MATRIX.relative_to(ROOT)),
        "sourceGoalAudit": str(GOAL_AUDIT.relative_to(ROOT)),
        "overallStatus": overall_status,
        "objectiveComplete": objective_complete,
        "completionClaimAllowed": objective_complete,
        "noCompletionClaim": not objective_complete,
        "counts": counts,
        "openRowCount": len(report_rows),
        "openRows": report_rows,
        "currentBlockingConditions": ["release_displayable"] if release.get("status") == "BLOCKED" else [],
        "currentPartialConditions": [
            condition
            for condition, active in (
                ("generation_reasoning_context", full_context.get("status") == "PARTIAL"),
                ("independent_model_tool_choice", independent_tool_choice.get("status") == "PARTIAL"),
            )
            if active
        ],
        "releaseNextAction": notarization.get("nextAction"),
        "longContextPolicy": {
            "provenSafeCeilingTokens": 192000,
            "aboveCeilingPolicy": "requires explicit high-risk override and fresh memory headroom",
            "modelLoadForAboveCeilingWithoutOverride": "refuse before model load",
        },
        "modelLoadBoundary": "no model load in this proof",
        "allEvidencePathsExist": True,
    }


def build_report(generated_at: str | None = None) -> dict[str, Any]:
    return build_report_from_payloads(
        load_json(MATRIX),
        load_json(GOAL_AUDIT),
        load_json(NOTARIZATION_PREFLIGHT),
        load_json(RELEASE_PUBLIC_TRUTH),
        generated_at=generated_at,
    )


def main() -> None:
    output = DEFAULT_OUTPUT
    report = build_report()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"objective open blockers proof wrote {output}")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"objective open blockers proof failed: {exc}", flush=True)
        raise SystemExit(1)
