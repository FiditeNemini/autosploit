#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/live-proofs/2026-07-04-pass-partial-blocked-matrix.json"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-goal-requirement-audit.json"
RELEASE_MANIFEST = ROOT / "release/release-manifest.json"


REQUIREMENTS = [
    {
        "id": "computer_use_live_gui",
        "requirement": "Use Computer Use for current live GUI/multiturn proof rather than only app/API proof.",
        "areas": ["Current Computer Use GUI attach/control", "Fully autonomous visible GUI demo"],
        "expectedStatus": "PASS",
    },
    {
        "id": "qwen27_prompt_cache_multiturn",
        "requirement": "Qwen3.6 27B MXFP8 MTP receives prompts, supports multiturn, and proves q4/prefix/paged/hybrid/block-L2 cache topology.",
        "areas": [
            "27B Qwen3.6 MXFP8 MTP engine load/cache",
            "27B visible UI bounded multiturn",
            "Real Qwen controls real installed safe-lab tools",
        ],
        "expectedStatus": "PASS",
    },
    {
        "id": "qwen35_prompt_cache_multiturn",
        "requirement": "Qwen3.6 35B A3B MXFP8 MTP receives prompts, supports multiturn, and proves q4/prefix/paged/hybrid/block-L2 cache topology.",
        "areas": [
            "35B Qwen3.6 A3B MXFP8 MTP engine load/cache",
            "35B visible UI bounded multiturn",
            "Real Qwen controls real installed safe-lab tools",
        ],
        "expectedStatus": "PASS",
    },
    {
        "id": "qwen_mtp_d3_output_path",
        "requirement": "Every selected Qwen model whose path/name contains MTP proves D3 MTP activation on the generation/output path.",
        "areas": ["Qwen MTP D3 output path"],
        "expectedStatus": "PASS",
    },
    {
        "id": "settings_model_selector_folder_scan",
        "requirement": "Settings exposes model selection, model folder adding/scanning, 27B/35B selection, and cache/runtime config state.",
        "areas": ["Settings model library scan/select", "Settings runtime/cache toggles take effect"],
        "expectedStatus": "PASS",
    },
    {
        "id": "generation_reasoning_context",
        "requirement": "Generation parameters, reasoning toggles, context budget, and full-context behavior are applied and verified.",
        "areas": [
            "Generation settings and context budget",
            "Reasoning-on final assistant content",
            "Full-context-length stress",
        ],
        "expectedStatus": "PARTIAL",
        "missingEvidence": "Reasoning-on final content and low-cap recovery are proven. 8k, 64k, 128k, 160k, and 192k long-context live Qwen completions are proven with post-generation cache writes. The 200k incremental retry and 224k graduated retry both reached live Qwen chunked prefill but failed safely after swapouts appeared; follow-up no-override proofs refuse above the 192k proven safe ceiling before model load unless an explicit high-risk override is set. Near-max resource preflight, target-token RAM refusal guard, exact-token route preflight, and 258k chunked-prefill entry are proven, but near-max final assistant output plus post-generation cache write proof are still missing.",
    },
    {
        "id": "verbose_tools_terminal_tabs",
        "requirement": "Tool usage, commands, active tab/workflow state, terminal toggle, transcripts, and raw results are visible.",
        "areas": ["Verbose chat-side tool transcript", "Terminal toggle and command transcript state"],
        "expectedStatus": "PASS",
    },
    {
        "id": "streaming_parser_reuse",
        "requirement": "Real streaming surfaces preserve content, reasoning, tool-call deltas, usage telemetry, parser reuse, and cache-reuse session metadata.",
        "areas": ["Streaming parser and SSE/tool delta coverage"],
        "expectedStatus": "PASS",
    },
    {
        "id": "autonomous_pentest_real_tools",
        "requirement": "Real models can autonomously drive safe pentest tools and phase workflows through the app loop.",
        "areas": [
            "Safe autonomous phase execution across recon/network/web/creds/exploit/post",
            "Real installed loopback/local tools",
            "Real Qwen controls real installed safe-lab tools",
            "Real Qwen controls Metasploit",
        ],
        "expectedStatus": "PASS",
    },
    {
        "id": "individual_toolchain_per_tool",
        "requirement": "Individual pentest tools have per-tool chat transcript, terminal transcript, and result/tab evidence.",
        "areas": ["Individual toolchain per-tool coverage"],
        "expectedStatus": "PASS",
    },
    {
        "id": "all_installed_tools_safe_smoke",
        "requirement": "Every installed Settings tool has bounded current-machine executable smoke coverage separate from model/exploit execution proof.",
        "areas": ["All installed tools safe smoke coverage"],
        "expectedStatus": "PASS",
    },
    {
        "id": "cve_library_current_intel",
        "requirement": "Modern CVE library/current threat intel is available and model-callable through app tools.",
        "areas": [
            "Modern CVE library and live feed refresh",
            "Model-invoked search_cve final-answer loop",
            "Model-invoked lookup_cve first-try argument preservation",
        ],
        "expectedStatus": "PASS",
    },
    {
        "id": "ram_lifecycle_guard",
        "requirement": "Repeated testing must not flood RAM; stale engine cleanup and fail-before-launch guards must be proven.",
        "areas": ["RAM/process lifecycle guard"],
        "expectedStatus": "PASS",
    },
    {
        "id": "release_displayable",
        "requirement": "Project is displayable/distributable enough for semi-functional demo handoff.",
        "areas": ["Release/distribution readiness"],
        "expectedStatus": "BLOCKED",
        "missingEvidence": "Local package, Developer ID signature, hardened runtime, and visible release smoke are proven, but notarization/distribution flow remains unrun: no accepted notary credential input/default keychain profile is configured, Gatekeeper rejects the app without notarization context, and app/DMG stapled tickets are missing.",
    },
]


STATUS_RANK = {"PASS": 0, "PARTIAL": 1, "BLOCKED": 2}


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:4000]
        raise AssertionError(message + suffix)


def aggregate_status(statuses: list[str]) -> str:
    require(statuses, "cannot aggregate empty status list")
    return max(statuses, key=lambda status: STATUS_RANK[status])


def status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {status: sum(1 for row in rows if row.get("status") == status) for status in ("PASS", "PARTIAL", "BLOCKED")}


def expected_matrix_counts_for_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = status_counts(rows)
    require(len(rows) == 26, "unexpected matrix row count", {"rowCount": len(rows)})
    require(sum(counts.values()) == len(rows), "matrix has rows with unsupported status", counts)
    return counts


def effective_expected_status(
    requirement: dict[str, Any],
    release_manifest: dict[str, Any] | None = None,
    evidence_rows: list[dict[str, Any]] | None = None,
) -> str:
    if requirement.get("id") == "release_displayable":
        gate = (release_manifest or {}).get("notarizationGate")
        require(
            gate in {"passed", "requires-notary-credentials"},
            "release manifest notarizationGate is not recognized",
            release_manifest,
        )
        return "PASS" if gate == "passed" else "BLOCKED"
    if requirement.get("id") == "generation_reasoning_context":
        rows = evidence_rows or []
        require(rows, "generation reasoning/context requirement needs matrix evidence rows")
        return "PASS" if all(row.get("status") == "PASS" for row in rows) else "PARTIAL"
    return requirement["expectedStatus"]


def completion_state(audit_rows: list[dict[str, Any]]) -> dict[str, Any]:
    require(audit_rows, "completion state needs audit rows")
    overall = aggregate_status([row["status"] for row in audit_rows])
    complete = overall == "PASS" and all(row["status"] == "PASS" for row in audit_rows)
    return {
        "objectiveComplete": complete,
        "completionClaimAllowed": complete,
        "overallStatus": overall,
    }


def release_manifest_evidence() -> dict[str, Any]:
    require(RELEASE_MANIFEST.is_file(), "release manifest is missing", str(RELEASE_MANIFEST))
    manifest = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))
    require(
        manifest.get("notarizationGate") in {"passed", "requires-notary-credentials"},
        "release manifest notarizationGate is not recognized",
        manifest,
    )
    artifacts = manifest.get("artifacts") or {}
    for key in ("appPath", "dmgPath"):
        path = artifacts.get(key)
        require(path and (ROOT / path).exists(), f"release manifest artifact missing: {key}", manifest)
    return {
        "manifest": str(RELEASE_MANIFEST.relative_to(ROOT)),
        "notarizationStatus": manifest.get("notarizationStatus"),
        "notarizationGate": manifest.get("notarizationGate"),
        "notarizationGateReason": manifest.get("notarizationGateReason"),
        "artifacts": artifacts,
    }


def main() -> None:
    output = DEFAULT_OUTPUT
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    rows = matrix.get("rows") or []
    by_area = {row.get("area"): row for row in rows}
    counts = status_counts(rows)
    missing_evidence_paths: list[str] = []
    for row in rows:
        for evidence in row.get("evidence") or []:
            if not (ROOT / evidence).exists():
                missing_evidence_paths.append(evidence)

    require(counts == expected_matrix_counts_for_rows(rows), "unexpected matrix status counts", counts)
    require(not missing_evidence_paths, "matrix has missing evidence paths", missing_evidence_paths)
    release_manifest = release_manifest_evidence()

    audit_rows: list[dict[str, Any]] = []
    for requirement in REQUIREMENTS:
        areas = requirement["areas"]
        missing_areas = [area for area in areas if area not in by_area]
        require(not missing_areas, f"requirement {requirement['id']} references missing matrix areas", missing_areas)
        evidence_rows = [by_area[area] for area in areas]
        status = aggregate_status([row["status"] for row in evidence_rows])
        expected_status = effective_expected_status(requirement, release_manifest, evidence_rows)
        require(status == expected_status, f"requirement {requirement['id']} status drifted", {
            "expected": expected_status,
            "actual": status,
            "areas": areas,
        })
        evidence = sorted({evidence for row in evidence_rows for evidence in (row.get("evidence") or [])})
        extra: dict[str, Any] = {}
        if requirement["id"] == "release_displayable":
            evidence.append(release_manifest["manifest"])
            extra["releaseManifest"] = release_manifest
        audit_row = {
            "id": requirement["id"],
            "requirement": requirement["requirement"],
            "status": status,
            "areas": areas,
            "evidence": sorted(set(evidence)),
            "missingEvidence": requirement.get("missingEvidence", ""),
        }
        audit_row.update(extra)
        audit_rows.append(audit_row)

    audit_counts = {status: sum(1 for row in audit_rows if row["status"] == status) for status in ("PASS", "PARTIAL", "BLOCKED")}
    completion = completion_state(audit_rows)
    report = {
        "ok": True,
        "proofType": "goal-requirement-audit",
        "proofLevel": "current-goal-pass-partial-blocked-matrix-backed",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sourceMatrix": str(MATRIX.relative_to(ROOT)),
        "objectiveComplete": completion["objectiveComplete"],
        "completionClaimAllowed": completion["completionClaimAllowed"],
        "overallStatus": completion["overallStatus"],
        "requirementCount": len(audit_rows),
        "statusCounts": audit_counts,
        "matrixStatusCounts": counts,
        "rows": audit_rows,
        "currentBlockingConditions": [
            row["id"] for row in audit_rows if row["status"] == "BLOCKED"
        ],
        "currentPartialConditions": [
            row["id"] for row in audit_rows if row["status"] == "PARTIAL"
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"goal requirement audit proof wrote {output}")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"goal requirement audit proof failed: {exc}", flush=True)
        raise SystemExit(1)
