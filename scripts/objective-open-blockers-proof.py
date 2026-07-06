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


OPEN_ROW_AREAS = {
    "Full-context-length stress",
    "Release/distribution readiness",
}


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
            "cache write evidence, but true near-max final assistant output plus post-generation "
            "cache write proof above that ceiling is still missing."
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


def build_report(generated_at: str | None = None) -> dict[str, Any]:
    matrix = load_json(MATRIX)
    goal_audit = load_json(GOAL_AUDIT)
    notarization = load_json(NOTARIZATION_PREFLIGHT)
    public_truth = load_json(RELEASE_PUBLIC_TRUTH)

    require(matrix.get("proofType") == "pass-partial-blocked-matrix", "unexpected matrix proof type", matrix)
    require(goal_audit.get("proofType") == "goal-requirement-audit", "unexpected goal audit proof type", goal_audit)
    require(notarization.get("proofType") == "notarization-preflight", "unexpected notarization proof type", notarization)
    require(public_truth.get("proofType") == "release-public-truth", "unexpected public release proof type", public_truth)
    require(goal_audit.get("objectiveComplete") is False, "goal audit must keep objective incomplete", goal_audit)
    require(goal_audit.get("completionClaimAllowed") is False, "goal audit must block completion claims", goal_audit)

    rows = matrix.get("rows") or []
    counts = matrix.get("statusCounts")
    require(counts == {"PASS": 24, "PARTIAL": 1, "BLOCKED": 1}, "unexpected matrix status counts", counts)
    require(matrix.get("rowCount") == 26, "unexpected matrix row count", matrix.get("rowCount"))
    missing_evidence = validate_evidence_paths(rows)
    require(not missing_evidence, "matrix has missing evidence paths", missing_evidence)

    by_area = {row.get("area"): row for row in rows}
    open_rows = [row for row in rows if row.get("status") in {"PARTIAL", "BLOCKED"}]
    require({row.get("area") for row in open_rows} == OPEN_ROW_AREAS, "unexpected open matrix rows", open_rows)

    goal_by_id = {row.get("id"): row for row in goal_audit.get("rows") or []}
    full_context = by_area["Full-context-length stress"]
    release = by_area["Release/distribution readiness"]
    require(full_context.get("status") == "PARTIAL", "full-context row status drifted", full_context)
    require(release.get("status") == "BLOCKED", "release row status drifted", release)

    report_rows = [
        build_full_context_row(full_context, goal_by_id["generation_reasoning_context"]),
        build_release_row(release, goal_by_id["release_displayable"], notarization, public_truth),
    ]

    report_missing_evidence = validate_evidence_paths(report_rows)
    require(not report_missing_evidence, "open blockers report has missing evidence paths", report_missing_evidence)

    return {
        "ok": True,
        "proofType": "objective-open-blockers",
        "proofLevel": "matrix-and-goal-audit-derived-no-model-load",
        "generatedAt": generated_at or time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sourceMatrix": str(MATRIX.relative_to(ROOT)),
        "sourceGoalAudit": str(GOAL_AUDIT.relative_to(ROOT)),
        "overallStatus": "BLOCKED",
        "objectiveComplete": False,
        "completionClaimAllowed": False,
        "noCompletionClaim": True,
        "counts": counts,
        "openRowCount": len(report_rows),
        "openRows": report_rows,
        "currentBlockingConditions": ["release_displayable"],
        "currentPartialConditions": ["generation_reasoning_context"],
        "releaseNextAction": notarization.get("nextAction"),
        "longContextPolicy": {
            "provenSafeCeilingTokens": 192000,
            "aboveCeilingPolicy": "requires explicit high-risk override and fresh memory headroom",
            "modelLoadForAboveCeilingWithoutOverride": "refuse before model load",
        },
        "modelLoadBoundary": "no model load in this proof",
        "allEvidencePathsExist": True,
    }


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
