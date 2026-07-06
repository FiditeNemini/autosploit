#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "docs/live-proofs/2026-07-04-pass-partial-blocked-matrix.json"
VALID_STATUSES = {"PASS", "PARTIAL", "BLOCKED"}


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:4000]
        raise AssertionError(message + suffix)


def status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {status: sum(1 for row in rows if row.get("status") == status) for status in ("PASS", "PARTIAL", "BLOCKED")}


def expected_counts_for_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = status_counts(rows)
    release_rows = [row for row in rows if row.get("area") == "Release/distribution readiness"]
    require(len(release_rows) == 1, "matrix must contain exactly one release readiness row", release_rows)
    release_status = release_rows[0].get("status")
    require(release_status in {"PASS", "BLOCKED"}, "release readiness row must be PASS or BLOCKED", release_rows[0])
    return counts


def validate_rows(rows: list[dict[str, Any]]) -> None:
    require(rows, "matrix rows cannot be empty")
    missing_evidence: list[str] = []
    invalid_rows: list[dict[str, Any]] = []
    duplicate_areas: list[str] = []
    seen_areas: set[str] = set()

    for index, row in enumerate(rows):
        area = row.get("area")
        status = row.get("status")
        evidence = row.get("evidence")
        if not isinstance(area, str) or not area.strip():
            invalid_rows.append({"index": index, "reason": "missing_area", "row": row})
        elif area in seen_areas:
            duplicate_areas.append(area)
        else:
            seen_areas.add(area)
        if status not in VALID_STATUSES:
            invalid_rows.append({"index": index, "reason": "invalid_status", "row": row})
        if not isinstance(evidence, list) or not evidence:
            invalid_rows.append({"index": index, "reason": "missing_evidence", "row": row})
            continue
        for rel_path in evidence:
            if not isinstance(rel_path, str) or not rel_path:
                invalid_rows.append({"index": index, "reason": "invalid_evidence_path", "row": row})
                continue
            if not (ROOT / rel_path).exists():
                missing_evidence.append(rel_path)

    require(not invalid_rows, "matrix has invalid rows", invalid_rows)
    require(not duplicate_areas, "matrix has duplicate areas", duplicate_areas)
    require(not missing_evidence, "matrix evidence paths are missing", sorted(set(missing_evidence)))


def build_report(
    matrix: dict[str, Any],
    generated_at: str | None = None,
    expected_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    rows = matrix.get("rows") or []
    require(isinstance(rows, list), "matrix rows must be a list")
    validate_rows(rows)
    counts = status_counts(rows)
    if expected_counts is not None:
        require(counts == expected_counts, "matrix status counts drifted", {"expected": expected_counts, "actual": counts})

    report = dict(matrix)
    report["ok"] = True
    report["proofType"] = "pass-partial-blocked-matrix"
    report["generatedAt"] = generated_at or timestamp()
    report["rowCount"] = len(rows)
    report["statusCounts"] = counts
    report["summary"] = {
        "pass": counts["PASS"],
        "partial": counts["PARTIAL"],
        "blocked": counts["BLOCKED"],
    }
    report["rows"] = rows
    return report


def main() -> None:
    matrix = json.loads(DEFAULT_MATRIX.read_text(encoding="utf-8"))
    rows = matrix.get("rows") or []
    report = build_report(matrix, expected_counts=expected_counts_for_rows(rows))
    DEFAULT_MATRIX.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"pass/partial/blocked matrix proof wrote {DEFAULT_MATRIX}")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"pass/partial/blocked matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
