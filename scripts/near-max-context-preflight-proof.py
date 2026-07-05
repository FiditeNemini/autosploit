#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_27B = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP")
SMOKE_ARTIFACT = ROOT / "docs/live-proofs/2026-07-04-real-qwen-long-context-smoke-27b.json"
NEAR_MAX_ATTEMPT_ARTIFACT = ROOT / "docs/live-proofs/2026-07-04-real-qwen-near-max-context-27b.json"
HIGH_TARGET_ATTEMPT_ARTIFACT = ROOT / "docs/live-proofs/2026-07-05-real-qwen-long-context-224k-27b.json"
INCREMENTAL_HIGH_TARGET_ATTEMPT_ARTIFACT = ROOT / "docs/live-proofs/2026-07-05-real-qwen-long-context-200k-27b.json"
INCREMENTAL_HIGH_TARGET_SAFETY_REFUSAL_ARTIFACT = ROOT / "docs/live-proofs/2026-07-05-long-context-200k-safety-refusal.json"
HIGH_TARGET_SAFETY_REFUSAL_ARTIFACT = ROOT / "docs/live-proofs/2026-07-05-long-context-224k-safety-refusal.json"
LONG_CONTEXT_ARTIFACTS = [
    ROOT / "docs/live-proofs/2026-07-04-real-qwen-long-context-smoke-27b.json",
    ROOT / "docs/live-proofs/2026-07-04-real-qwen-long-context-64k-27b.json",
    ROOT / "docs/live-proofs/2026-07-04-real-qwen-long-context-128k-27b.json",
    ROOT / "docs/live-proofs/2026-07-04-real-qwen-long-context-160k-27b.json",
    ROOT / "docs/live-proofs/2026-07-04-real-qwen-long-context-192k-27b.json",
]
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-near-max-context-preflight.json"
NEAR_MAX_TARGET_TOKENS = 258_000
REQUIRED_AVAILABLE_GB = 80.0
PROVEN_SAFE_TARGET_CEILING = 192_000


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def run(cmd: list[str], timeout: float = 15.0) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return {
            "cmd": cmd,
            "timeout": timeout,
            "stdout": stdout[-12000:],
            "stderr": stderr[-12000:],
        }


def parse_memory_pressure(output: str) -> dict[str, Any]:
    free_match = re.search(r"System-wide memory free percentage:\s*(\d+)%", output)
    swapout_match = re.search(r"Swapouts:\s*(\d+)", output)
    free_percent = int(free_match.group(1)) if free_match else None
    swapouts = int(swapout_match.group(1)) if swapout_match else None
    total_gb = 128.0
    available_gb = round((total_gb * free_percent / 100.0), 2) if free_percent is not None else None
    return {
        "freePercent": free_percent,
        "swapouts": swapouts,
        "availableGBEstimate": available_gb,
        "requiredAvailableGB": REQUIRED_AVAILABLE_GB,
        "status": "PASS" if available_gb is not None and available_gb >= REQUIRED_AVAILABLE_GB else "BLOCKED",
    }


def heavy_model_processes() -> list[dict[str, Any]]:
    proc = subprocess.run(
        ["/bin/ps", "axo", "pid,ppid,rss,etime,command"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=15.0,
    )
    rows: list[dict[str, Any]] = []
    patterns = ("vmlx_engine.server", "ExploitBotEngine/launch.py", "Qwen3.6", "osaurus-evals")
    for line in proc.stdout.splitlines()[1:]:
        if not any(pattern in line for pattern in patterns):
            continue
        parts = line.split(None, 4)
        if len(parts) != 5:
            continue
        pid, ppid, rss, elapsed, command = parts
        if "near-max-context-preflight-proof.py" in command:
            continue
        rows.append(
            {
                "pid": int(pid),
                "ppid": int(ppid),
                "rssKB": int(rss),
                "elapsed": elapsed,
                "command": command,
            }
        )
    return rows


def model_context_contract(model: Path) -> dict[str, Any]:
    config = json.loads((model / "config.json").read_text(encoding="utf-8"))
    tokenizer_config = json.loads((model / "tokenizer_config.json").read_text(encoding="utf-8"))
    text_config = config.get("text_config") or {}
    return {
        "configTextMaxPositionEmbeddings": text_config.get("max_position_embeddings"),
        "tokenizerModelMaxLength": tokenizer_config.get("model_max_length"),
        "modelType": config.get("model_type"),
        "textModelType": text_config.get("model_type"),
        "ropeParameters": text_config.get("rope_parameters"),
    }


def smoke_status(smoke: dict[str, Any]) -> dict[str, Any]:
    status = smoke.get("status") or {}
    required = [
        "declared262kContext",
        "lowerPerRequestCapRejected",
        "longPromptCompleted",
        "usagePromptTokensReported",
        "q4KV",
        "prefixCache",
        "pagedCache",
        "hybridSSM",
        "blockL2",
    ]
    return {
        "requiredRows": required,
        "missingRows": [key for key in required if key not in status],
        "failedRows": [key for key in required if status.get(key) != "PASS"],
        "actualPromptTokensByTokenizer": smoke.get("actualPromptTokensByTokenizer"),
        "usagePromptTokens": (smoke.get("usage") or {}).get("prompt_tokens"),
        "sessionMaxPromptTokens": smoke.get("sessionMaxPromptTokens"),
        "generatedAt": smoke.get("generatedAt"),
        "targetPromptTokens": smoke.get("targetPromptTokens"),
    }


def completed_long_context_proofs(paths: list[Path]) -> list[dict[str, Any]]:
    proofs: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        artifact = json.loads(path.read_text(encoding="utf-8"))
        summary = smoke_status(artifact)
        summary["ok"] = artifact.get("ok") is True
        if not summary["ok"] or summary["missingRows"] or summary["failedRows"]:
            continue
        proofs.append({
            "artifact": str(path.relative_to(ROOT)),
            "targetPromptTokens": artifact.get("targetPromptTokens"),
            "summary": summary,
        })
    return sorted(
        proofs,
        key=lambda row: int((row.get("summary") or {}).get("actualPromptTokensByTokenizer") or 0),
    )


def near_max_attempt_summary(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    artifact = json.loads(path.read_text(encoding="utf-8"))
    guard = artifact.get("completionMemoryGuard") or {}
    samples = guard.get("samples") or []
    min_free = None
    max_swapouts = None
    if samples:
        free_values = [sample.get("freePercent") for sample in samples if sample.get("freePercent") is not None]
        swapout_values = [sample.get("swapouts") for sample in samples if sample.get("swapouts") is not None]
        min_free = min(free_values) if free_values else None
        max_swapouts = max(swapout_values) if swapout_values else None
    return {
        "artifact": str(path.relative_to(ROOT)),
        "ok": artifact.get("ok") is True,
        "generatedAt": artifact.get("generatedAt"),
        "targetPromptTokens": artifact.get("targetPromptTokens"),
        "actualPromptTokensByTokenizer": artifact.get("actualPromptTokensByTokenizer"),
        "sessionMaxPromptTokens": artifact.get("sessionMaxPromptTokens"),
        "error": artifact.get("error"),
        "completionMemoryGuard": {
            "enabled": guard.get("enabled") is True,
            "aborted": guard.get("aborted") is True,
            "abortReason": guard.get("abortReason"),
            "abortFreePercent": guard.get("abortFreePercent"),
            "sampleCount": len(samples),
            "minFreePercent": min_free,
            "maxSwapouts": max_swapouts,
        },
        "targetMemoryPreflight": artifact.get("targetMemoryPreflight"),
    }


def safety_refusal_summary(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    artifact = json.loads(path.read_text(encoding="utf-8"))
    preflight = artifact.get("targetMemoryPreflight") or {}
    return {
        "artifact": str(path.relative_to(ROOT)),
        "ok": artifact.get("ok") is True,
        "generatedAt": artifact.get("generatedAt"),
        "targetPromptTokens": artifact.get("targetPromptTokens"),
        "error": artifact.get("error"),
        "lastBlockReason": (preflight.get("memorySlotWait") or {}).get("lastBlockReason"),
        "provenSafeTargetCeiling": preflight.get("provenSafeTargetCeiling"),
        "allowUnprovenNearMaxTarget": preflight.get("allowUnprovenNearMaxTarget"),
        "overrideEnv": preflight.get("unprovenTargetOverrideEnv"),
        "engineLogTailEmpty": artifact.get("engineLogTail") == "",
    }


def build_report(
    *,
    model: Path,
    completed_proofs: list[dict[str, Any]],
    memory: dict[str, Any],
    processes: list[dict[str, Any]],
    near_max_attempt: dict[str, Any] | None = None,
    incremental_high_target_attempt: dict[str, Any] | None = None,
    incremental_high_target_safety_refusal: dict[str, Any] | None = None,
    high_target_attempt: dict[str, Any] | None = None,
    high_target_safety_refusal: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    declared = model_context_contract(model)
    declared_max = declared.get("configTextMaxPositionEmbeddings")
    tokenizer_max = declared.get("tokenizerModelMaxLength")
    largest_completed = max(
        (int((row.get("summary") or {}).get("actualPromptTokensByTokenizer") or 0) for row in completed_proofs),
        default=0,
    )
    remaining_gap = max(0, int(declared_max or 0) - largest_completed)
    process_status = "PASS" if not processes else "BLOCKED"
    resource_status = "PASS" if memory.get("status") == "PASS" and process_status == "PASS" else "BLOCKED"
    smoke_topology_status = (
        "PASS"
        if completed_proofs and all(
            not (row.get("summary") or {}).get("missingRows") and not (row.get("summary") or {}).get("failedRows")
            for row in completed_proofs
        )
        else "FAIL"
    )
    if near_max_attempt is None:
        near_max_live_status = "NOT_RUN_EXPLICIT_RESOURCE_GATED"
        missing_evidence = (
            "No real near-max 262144-token model generation artifact exists yet. "
            "Run explicitNearMaxRunCommand only when the machine is reserved for a long Qwen context stress run."
        )
    elif near_max_attempt.get("ok") is True:
        near_max_live_status = "PASS"
        missing_evidence = ""
    else:
        near_max_live_status = "FAILED_GUARDED_ATTEMPT"
        missing_evidence = (
            "A real 258k near-max Qwen attempt exists, but it did not complete final assistant output "
            "or post-generation cache writes. The latest attempt reached "
            f"{near_max_attempt.get('actualPromptTokensByTokenizer')} tokenizer-counted prompt tokens and ended with "
            f"{near_max_attempt.get('error')}."
        )
    high_target_note = ""
    if incremental_high_target_attempt and (incremental_high_target_attempt.get("completionMemoryGuard") or {}).get("abortReason"):
        guard = incremental_high_target_attempt.get("completionMemoryGuard") or {}
        high_target_note += (
            f" A 200k incremental retry also failed safely with {guard.get('abortReason')} "
            f"after reaching {incremental_high_target_attempt.get('actualPromptTokensByTokenizer')} "
            "tokenizer-counted prompt tokens and entering live chunked prefill."
        )
    if high_target_attempt and (high_target_attempt.get("completionMemoryGuard") or {}).get("abortReason"):
        guard = high_target_attempt.get("completionMemoryGuard") or {}
        high_target_note += (
            f" A 224k graduated retry also failed safely with {guard.get('abortReason')} "
            f"after reaching {high_target_attempt.get('actualPromptTokensByTokenizer')} tokenizer-counted prompt tokens."
        )
    if high_target_note:
        missing_evidence += high_target_note
    explicit_command = [
        "env",
        "EXPLOITBOT_LONG_CONTEXT_ALLOW_UNPROVEN_TARGET=1",
        "EXPLOITBOT_LONG_CONTEXT_TARGET_TOKENS=258000",
        "EXPLOITBOT_LONG_CONTEXT_TIMEOUT=3600",
        "PYTHONPATH=ExploitBotEngine",
        "ExploitBotEngine/.venv/bin/python3",
        "scripts/real-qwen-long-context-smoke-proof.py",
    ]
    return {
        "ok": True,
        "proofType": "near-max-context-preflight",
        "proofLevel": "source-config-smoke-artifact-and-resource-preflight",
        "generatedAt": generated_at or timestamp(),
        "model": str(model),
        "declaredContext": declared,
        "declaredMaxContextTokens": declared_max,
        "tokenizerMaxLength": tokenizer_max,
        "nearMaxTargetPromptTokens": NEAR_MAX_TARGET_TOKENS,
        "smokeArtifact": str(SMOKE_ARTIFACT.relative_to(ROOT)),
        "completedLongContextProofs": completed_proofs,
        "nearMaxAttempt": near_max_attempt,
        "incrementalHighTargetAttempt": incremental_high_target_attempt,
        "incrementalHighTargetSafetyRefusal": incremental_high_target_safety_refusal,
        "highTargetAttempt": high_target_attempt,
        "highTargetSafetyRefusal": high_target_safety_refusal,
        "largestCompletedPromptTokens": largest_completed,
        "unprovenGapTokens": remaining_gap,
        "provenSafeTargetCeiling": PROVEN_SAFE_TARGET_CEILING,
        "unprovenTargetOverrideEnv": "EXPLOITBOT_LONG_CONTEXT_ALLOW_UNPROVEN_TARGET",
        "memoryPreflight": memory,
        "heavyModelProcesses": processes,
        "explicitNearMaxRunCommand": explicit_command,
        "status": {
            "declared262kContext": "PASS" if declared_max == 262144 and tokenizer_max == 262144 else "FAIL",
            "smokeTopologyProof": smoke_topology_status,
            "resourcePreflight": resource_status,
            "nearMaxLiveStatus": near_max_live_status,
        },
        "missingEvidence": missing_evidence,
    }


def main() -> None:
    output = Path(os.environ.get("EXPLOITBOT_NEAR_MAX_CONTEXT_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    model = Path(os.environ.get("EXPLOITBOT_NEAR_MAX_CONTEXT_MODEL", str(MODEL_27B))).expanduser()
    if not model.is_dir():
        raise SystemExit(f"model folder missing: {model}")
    memory_output = run(["/usr/bin/memory_pressure"]).get("stdout", "")
    report = build_report(
        model=model,
        completed_proofs=completed_long_context_proofs(LONG_CONTEXT_ARTIFACTS),
        memory=parse_memory_pressure(memory_output),
        processes=heavy_model_processes(),
        near_max_attempt=near_max_attempt_summary(NEAR_MAX_ATTEMPT_ARTIFACT),
        incremental_high_target_attempt=near_max_attempt_summary(INCREMENTAL_HIGH_TARGET_ATTEMPT_ARTIFACT),
        incremental_high_target_safety_refusal=safety_refusal_summary(INCREMENTAL_HIGH_TARGET_SAFETY_REFUSAL_ARTIFACT),
        high_target_attempt=near_max_attempt_summary(HIGH_TARGET_ATTEMPT_ARTIFACT),
        high_target_safety_refusal=safety_refusal_summary(HIGH_TARGET_SAFETY_REFUSAL_ARTIFACT),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"near-max context preflight proof wrote {output}")


if __name__ == "__main__":
    main()
