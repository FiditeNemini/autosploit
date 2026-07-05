#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-qwen-d3-mtp-output-proof.json"
DEFAULT_ARTIFACTS = [
    ROOT / "docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-27b.json",
    ROOT / "docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-35b.json",
]


def nested_get(value: Any, path: list[Any]) -> Any:
    current = value
    for part in path:
        if isinstance(part, int):
            if not isinstance(current, list) or part >= len(current):
                return None
            current = current[part]
            continue
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def first_value(value: Any, paths: list[list[Any]]) -> Any:
    for path in paths:
        found = nested_get(value, path)
        if found is not None:
            return found
    return None


def numeric(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def list_number(value: Any, index: int) -> float:
    if isinstance(value, list) and index < len(value):
        return numeric(value[index])
    return 0.0


def final_assistant_output_produced(artifact: dict[str, Any]) -> bool:
    messages = first_value(
        artifact,
        [
            ["phaseAttempts", 0, "messages"],
            ["messages"],
        ],
    )
    if not isinstance(messages, list):
        return False
    assistant_messages = [
        message for message in messages
        if isinstance(message, dict) and message.get("role") == "assistant"
    ]
    if not assistant_messages:
        return False
    content = assistant_messages[-1].get("content")
    return isinstance(content, str) and bool(content.strip())


def extract_d3_mtp_output_evidence(
    artifact: dict[str, Any],
    artifact_path: Path,
) -> dict[str, Any]:
    model_path = first_value(artifact, [["model"], ["modelPath"], ["health", "model", "path"]])
    model_text = str(model_path or "")
    mtp_stats = first_value(
        artifact,
        [
            ["phaseAttempts", 0, "cacheStats", "scheduler_stats", "batch_generator", "last_native_mtp"],
            ["phaseAttempts", 0, "engineHealth", "scheduler", "batch_generator", "last_native_mtp"],
            ["cacheStats", "scheduler_stats", "batch_generator", "last_native_mtp"],
            ["engineHealth", "scheduler", "batch_generator", "last_native_mtp"],
            ["health", "scheduler", "batch_generator", "last_native_mtp"],
        ],
    )
    health_mtp = first_value(
        artifact,
        [
            ["health", "mtp"],
            ["engineHealth", "mtp"],
            ["phaseAttempts", 0, "engineHealth", "mtp"],
        ],
    )
    if not isinstance(health_mtp, dict):
        health_mtp = {}
    if not isinstance(mtp_stats, dict):
        mtp_stats = {}

    drafted_by_depth = mtp_stats.get("drafted_by_depth")
    accepted_by_depth = mtp_stats.get("accepted_by_depth")
    forwards = mtp_stats.get("forwards") if isinstance(mtp_stats.get("forwards"), dict) else {}
    effective_depth = numeric(health_mtp.get("effective_depth"))
    d3_drafted = list_number(drafted_by_depth, 2)
    d3_accepted = list_number(accepted_by_depth, 2)
    mtp_forwards = numeric(forwards.get("mtp"))
    final_output = final_assistant_output_produced(artifact)

    checks = {
        "artifactOk": artifact.get("ok") is True,
        "modelNameContainsQwen": "qwen" in model_text.lower(),
        "modelNameContainsMTP": "mtp" in model_text.lower(),
        "runtimeActive": health_mtp.get("runtime_active") is True,
        "bundleHasMTP": health_mtp.get("runtime_bundle_has_mtp") is True,
        "effectiveDepthAtLeast3": effective_depth >= 3,
        "lastNativeMTPPresent": bool(mtp_stats),
        "d3DraftedTokensPresent": d3_drafted > 0,
        "d3AcceptedTokensPresent": d3_accepted > 0,
        "mtpForwardPassesPresent": mtp_forwards > 0,
        "acceptedOutputTokensPresent": numeric(mtp_stats.get("accepted_tokens")) > 0,
        "draftedOutputTokensPresent": numeric(mtp_stats.get("drafted_tokens")) > 0,
        "noMTPFallback": mtp_stats.get("fallback_reason") in {None, ""},
        "finalAssistantOutputProduced": final_output,
    }
    failure_names = {
        "artifactOk": "artifact_not_ok",
        "modelNameContainsQwen": "model_name_not_qwen",
        "modelNameContainsMTP": "model_name_missing_mtp",
        "runtimeActive": "runtime_mtp_not_active",
        "bundleHasMTP": "runtime_bundle_has_mtp_not_true",
        "effectiveDepthAtLeast3": "effective_depth_less_than_3",
        "lastNativeMTPPresent": "missing_last_native_mtp",
        "d3DraftedTokensPresent": "missing_d3_drafted_tokens",
        "d3AcceptedTokensPresent": "missing_d3_accepted_tokens",
        "mtpForwardPassesPresent": "missing_mtp_forward_passes",
        "acceptedOutputTokensPresent": "missing_accepted_output_tokens",
        "draftedOutputTokensPresent": "missing_drafted_output_tokens",
        "noMTPFallback": "mtp_fallback_reason_present",
        "finalAssistantOutputProduced": "missing_final_assistant_output",
    }
    failures = [failure_names[name] for name, passed in checks.items() if not passed]

    return {
        "artifact": str(artifact_path),
        "status": "PASS" if not failures else "FAIL",
        "modelPath": model_path,
        "modelNameContainsMTP": checks["modelNameContainsMTP"],
        "runtimeActive": checks["runtimeActive"],
        "bundleHasMTP": checks["bundleHasMTP"],
        "effectiveDepth": int(effective_depth),
        "finishReason": mtp_stats.get("finish_reason"),
        "finalDepth": mtp_stats.get("final_depth"),
        "draftedTokens": mtp_stats.get("drafted_tokens"),
        "acceptedTokens": mtp_stats.get("accepted_tokens"),
        "d3DraftedTokens": int(d3_drafted),
        "d3AcceptedTokens": int(d3_accepted),
        "depthAcceptanceRates": mtp_stats.get("depth_acceptance_rates"),
        "mtpForwardPasses": int(mtp_forwards),
        "fallbackReason": mtp_stats.get("fallback_reason"),
        "finalAssistantOutputProduced": final_output,
        "checks": checks,
        "failures": failures,
    }


def main() -> None:
    rows = []
    for artifact_path in DEFAULT_ARTIFACTS:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        rows.append(
            extract_d3_mtp_output_evidence(
                artifact,
                artifact_path=artifact_path.relative_to(ROOT),
            )
        )

    report = {
        "ok": all(row["status"] == "PASS" for row in rows),
        "proofType": "qwen-d3-mtp-output-path",
        "proofLevel": "existing-live-artifact-runtime-decode-counter-backed",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "requirement": "Every Qwen model with MTP in the selected path/name must prove D3 MTP activation on the generation/output path.",
        "rows": rows,
        "statusCounts": {
            "PASS": sum(1 for row in rows if row["status"] == "PASS"),
            "FAIL": sum(1 for row in rows if row["status"] == "FAIL"),
        },
    }
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["ok"]:
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(f"qwen D3 MTP output proof wrote {DEFAULT_OUTPUT}")


if __name__ == "__main__":
    main()
