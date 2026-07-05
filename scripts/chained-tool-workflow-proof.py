#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-chained-tool-workflow.json"

CHAIN_ARTIFACTS = [
    {
        "id": "real_installed_loopback_chain",
        "artifact": ROOT / "docs/live-proofs/2026-07-04-real-installed-tools-loopback.json",
        "requiredTools": ["nmap", "httpx", "nuclei", "hydra", "netexec", "linpeas", "run_shell", "run_shell"],
        "finalMarker": "REAL_INSTALLED_TOOLS_FINAL",
        "modelRequired": False,
    },
    {
        "id": "qwen27_real_installed_loopback_chain",
        "artifact": ROOT / "docs/live-proofs/2026-07-04-real-qwen-real-tools-loopback-27b.json",
        "requiredTools": ["nmap", "httpx", "nuclei", "hydra", "netexec", "linpeas", "run_shell", "run_shell"],
        "finalMarker": "REAL_QWEN_REAL_TOOLS_FINAL",
        "modelRequired": True,
    },
    {
        "id": "qwen35_real_installed_loopback_chain",
        "artifact": ROOT / "docs/live-proofs/2026-07-04-real-qwen-real-tools-loopback-35b.json",
        "requiredTools": ["nmap", "httpx", "nuclei", "hydra", "netexec", "linpeas", "run_shell", "run_shell"],
        "finalMarker": "REAL_QWEN_REAL_TOOLS_FINAL",
        "modelRequired": True,
    },
    {
        "id": "qwen27_phase_chain",
        "artifact": ROOT / "docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-27b.json",
        "requiredTools": ["nmap", "netexec", "sqlmap", "hydra", "metasploit", "linpeas"],
        "finalMarker": "REAL_QWEN_PHASE_FINAL",
        "modelRequired": True,
    },
    {
        "id": "qwen35_phase_chain",
        "artifact": ROOT / "docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-35b.json",
        "requiredTools": ["nmap", "netexec", "sqlmap", "hydra", "metasploit", "linpeas"],
        "finalMarker": "REAL_QWEN_PHASE_FINAL",
        "modelRequired": True,
    },
]


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def all_messages(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    messages = [row for row in artifact.get("messages") or [] if isinstance(row, dict)]
    for attempt in artifact.get("phaseAttempts") or []:
        if isinstance(attempt, dict):
            messages.extend(row for row in attempt.get("messages") or [] if isinstance(row, dict))
    return messages


def tool_call_sequence(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, message in enumerate(messages):
        tool = str(message.get("tool") or "").strip()
        content = str(message.get("content") or "")
        if not tool and content.lower().startswith("tool request: "):
            first = content.splitlines()[0]
            tool = first.split(":", 1)[-1].strip()
        if message.get("role") == "toolCall" and tool:
            rows.append(
                {
                    "index": index,
                    "tool": tool,
                    "status": message.get("status"),
                    "contentPreview": content[:280],
                }
            )
    return rows


def ordered_subsequence_positions(actual: list[str], expected: list[str]) -> list[int] | None:
    positions = []
    cursor = 0
    for expected_tool in expected:
        while cursor < len(actual) and actual[cursor] != expected_tool:
            cursor += 1
        if cursor >= len(actual):
            return None
        positions.append(cursor)
        cursor += 1
    return positions


def final_marker_after_chain(messages: list[dict[str, Any]], marker: str, last_tool_message_index: int | None) -> bool:
    if last_tool_message_index is None:
        return False
    for message in messages[last_tool_message_index + 1:]:
        if message.get("role") == "assistant" and marker in str(message.get("content") or ""):
            return True
    return False


def cache_proof(artifact: dict[str, Any]) -> dict[str, Any]:
    cache = artifact.get("cacheAfter") or {}
    for attempt in artifact.get("phaseAttempts") or []:
        if isinstance(attempt, dict) and isinstance(attempt.get("cacheStats"), dict):
            cache = attempt["cacheStats"]
            break
    native = cache.get("native_cache") or {}
    kvq = cache.get("kv_cache_quantization") or {}
    block = cache.get("block_disk_cache") or {}
    scheduler = cache.get("scheduler_cache") or {}
    totals = cache.get("cache_totals") or {}
    return {
        "q4KV": kvq.get("enabled") is True and int(kvq.get("bits") or 0) == 4,
        "hybridSSM": native.get("cache_type") == "hybrid_ssm_typed",
        "paged": native.get("paged") is True,
        "prefix": native.get("prefix") is True,
        "blockL2Tokens": block.get("total_tokens_on_disk") or totals.get("l2_block_tokens_on_disk") or 0,
        "schedulerCachedTokens": scheduler.get("total_tokens_cached") or 0,
    }


def build_chain_row(spec: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    messages = all_messages(artifact)
    calls = tool_call_sequence(messages)
    actual_tools = [row["tool"] for row in calls]
    positions = ordered_subsequence_positions(actual_tools, spec["requiredTools"])
    last_call_message_index = calls[positions[-1]]["index"] if positions else None
    final_after_chain = final_marker_after_chain(messages, spec["finalMarker"], last_call_message_index)
    cache = cache_proof(artifact)
    model = artifact.get("model")
    required_cache_pass = (
        not spec.get("modelRequired")
        or (cache["q4KV"] and cache["hybridSSM"] and cache["paged"] and cache["prefix"])
    )
    failures = []
    if artifact.get("ok") is not True:
        failures.append("artifact_not_ok")
    if spec.get("modelRequired") and not model:
        failures.append("missing_model_path")
    if positions is None:
        failures.append("missing_ordered_tool_subsequence")
    if not final_after_chain:
        failures.append("missing_final_assistant_after_chain")
    if not required_cache_pass:
        failures.append("missing_model_cache_proof")
    return {
        "id": spec["id"],
        "artifact": str(spec["artifact"].relative_to(ROOT)),
        "status": "PASS" if not failures else "FAIL",
        "model": model,
        "requiredTools": spec["requiredTools"],
        "observedTools": actual_tools,
        "orderedPositions": positions,
        "finalMarker": spec["finalMarker"],
        "finalMarkerAfterChain": final_after_chain,
        "cacheProof": cache,
        "toolCallPreviews": calls,
        "failures": failures,
    }


def build_report(*, generated_at: str | None = None) -> dict[str, Any]:
    rows = []
    for spec in CHAIN_ARTIFACTS:
        artifact = json.loads(spec["artifact"].read_text(encoding="utf-8"))
        rows.append(build_chain_row(spec, artifact))
    return {
        "ok": all(row["status"] == "PASS" for row in rows),
        "proofType": "chained-tool-workflow",
        "proofLevel": "existing-live-artifact-ordered-transcript-backed",
        "generatedAt": generated_at or timestamp(),
        "requirement": (
            "Autonomous tool proof must show ordered multi-tool chains plus final model continuation, "
            "not only individual per-tool evidence."
        ),
        "rowCount": len(rows),
        "statusCounts": {
            "PASS": sum(1 for row in rows if row["status"] == "PASS"),
            "FAIL": sum(1 for row in rows if row["status"] == "FAIL"),
        },
        "rows": rows,
    }


def main() -> None:
    output = DEFAULT_OUTPUT
    report = build_report()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["ok"]:
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(f"chained tool workflow proof wrote {output}")


if __name__ == "__main__":
    main()
