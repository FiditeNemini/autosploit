#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-qwen-runtime-readiness.json"

MODEL_ARTIFACTS = {
    "27b": ROOT / "docs/live-proofs/2026-07-04-real-qwen-real-tools-loopback-27b.json",
    "35b": ROOT / "docs/live-proofs/2026-07-04-real-qwen-real-tools-loopback-35b.json",
}
REASONING_ARTIFACTS = {
    "27b": ROOT / "docs/live-proofs/2026-07-04-real-qwen-27b-reasoning-on-1024.json",
    "35b": ROOT / "docs/live-proofs/2026-07-04-real-qwen-35b-reasoning-on-1024.json",
}
D3_MTP_ARTIFACT = ROOT / "docs/live-proofs/2026-07-04-qwen-d3-mtp-output-proof.json"
STREAMING_ARTIFACT = ROOT / "docs/live-proofs/2026-07-04-streaming-parser-reuse.json"
CVE_LOOKUP_ARTIFACT = ROOT / "docs/live-proofs/2026-07-04-real-qwen-35b-lookup-cve-first-try.json"
LONG_CONTEXT_ARTIFACT = ROOT / "docs/live-proofs/2026-07-04-real-qwen-long-context-smoke-27b.json"


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


def numeric(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def model_text(artifact: dict[str, Any]) -> str:
    return str(
        artifact.get("model")
        or artifact.get("modelPath")
        or nested_get(artifact, ["health", "effective_config", "model", "path"])
        or nested_get(artifact, ["health", "model_name"])
        or ""
    )


def messages_text(artifact: dict[str, Any]) -> str:
    return json.dumps(artifact.get("messages") or [], sort_keys=True)


def evaluate_model(
    label: str,
    artifact: dict[str, Any],
    d3_row: dict[str, Any] | None,
    artifact_path: Path,
) -> dict[str, Any]:
    cache = artifact.get("cacheAfter") or {}
    health = artifact.get("health") or {}
    native = cache.get("native_cache") or {}
    scheduler = cache.get("scheduler_cache") or {}
    cache_totals = cache.get("cache_totals") or {}
    ssm = cache.get("ssm_companion") or {}
    ssm_disk = ssm.get("disk") or {}
    effective = health.get("effective_config") or {}
    parsers = effective.get("parsers") or {}
    effective_cache = effective.get("cache") or {}
    topology = effective_cache.get("topology") or {}
    storage_quant = native.get("attention_kv_storage_quantization") or {}
    text = messages_text(artifact)
    path_text = model_text(artifact)
    d3_row = d3_row or {}

    checks = {
        "artifactOk": artifact.get("ok") is True,
        "modelNameQwenMXFP8MTP": all(part in path_text.lower() for part in ("qwen", "mxfp8", "mtp")),
        "q4TurboQuantKV": (cache.get("kv_cache_quantization") or {}).get("enabled") is True
        and int((cache.get("kv_cache_quantization") or {}).get("bits") or 0) == 4
        and (effective_cache.get("kv_cache_quantization") or {}).get("mode") == "turboquant-q4",
        "hybridAsyncRederive": native.get("cache_type") == "hybrid_ssm_typed"
        and "async_rederive" in (native.get("components") or [])
        and storage_quant.get("enabled") is True
        and int(storage_quant.get("bits") or 0) == 4
        and storage_quant.get("rederive") == "async_clean_prefill_on_miss_or_warm_pass",
        "prefixPagedBlockL2": native.get("prefix") is True
        and native.get("paged") is True
        and native.get("block_disk_l2") is True
        and int(scheduler.get("block_size") or 0) > 0
        and int(scheduler.get("total_tokens_cached") or 0) > 0
        and numeric(cache_totals.get("l2_block_tokens_on_disk")) > 0,
        "ssmCompanionDiskL2": ssm.get("disk_enabled") is True
        and numeric(cache_totals.get("ssm_tokens_on_disk")) > 0
        and numeric(ssm_disk.get("stores")) > 0,
        "qwenParsers": parsers.get("reasoning") == "qwen3"
        and parsers.get("tool_call") == "qwen",
        "topologyContract": topology.get("name") == "hybrid_ssm_attention"
        and topology.get("block_l2_active") is True
        and topology.get("ssm_companion_required") is True,
        "toolTranscriptVisible": artifact.get("chatContainsRealToolOutput") is True
        and artifact.get("terminalContainsRealToolOutput") is True
        and artifact.get("resultsContainRealToolOutput") is True
        and "Tool request:" in text,
        "d3MTPOutputPath": d3_row.get("status") == "PASS"
        and int(d3_row.get("effectiveDepth") or 0) >= 3
        and int(d3_row.get("d3DraftedTokens") or 0) > 0
        and int(d3_row.get("d3AcceptedTokens") or 0) > 0
        and int(d3_row.get("mtpForwardPasses") or 0) > 0
        and d3_row.get("finalAssistantOutputProduced") is True,
    }
    failure_names = {
        "artifactOk": "artifact_not_ok",
        "modelNameQwenMXFP8MTP": "model_name_missing_qwen_mxfp8_mtp",
        "q4TurboQuantKV": "q4_turboquant_kv_missing",
        "hybridAsyncRederive": "hybrid_async_rederive_missing",
        "prefixPagedBlockL2": "prefix_paged_block_l2_missing",
        "ssmCompanionDiskL2": "ssm_companion_disk_l2_missing",
        "qwenParsers": "qwen_parsers_missing",
        "topologyContract": "hybrid_topology_contract_missing",
        "toolTranscriptVisible": "tool_transcript_not_visible",
        "d3MTPOutputPath": "d3_mtp_output_path_missing",
    }
    failures = [failure_names[name] for name, ok in checks.items() if not ok]
    return {
        "label": label,
        "status": "PASS" if not failures else "FAIL",
        "artifact": str(artifact_path),
        "model": path_text,
        "checks": checks,
        "failures": failures,
        "cacheEvidence": {
            "q4TurboQuantKV": (effective_cache.get("kv_cache_quantization") or {}),
            "q4KV": cache.get("kv_cache_quantization"),
            "ssmCompanionNotQuantized": storage_quant,
            "nativeCache": {
                "cache_type": native.get("cache_type"),
                "components": native.get("components"),
                "paged": native.get("paged"),
                "prefix": native.get("prefix"),
                "block_disk_l2": native.get("block_disk_l2"),
                "attention_kv_storage_quantization": storage_quant,
            },
            "scheduler": {
                "block_size": scheduler.get("block_size"),
                "total_tokens_cached": scheduler.get("total_tokens_cached"),
                "tokens_saved": scheduler.get("tokens_saved"),
            },
            "cacheTotals": {
                "l2_block_tokens_on_disk": cache_totals.get("l2_block_tokens_on_disk"),
                "ssm_tokens_on_disk": cache_totals.get("ssm_tokens_on_disk"),
            },
        },
        "parserEvidence": parsers,
        "d3Evidence": {
            "effectiveDepth": d3_row.get("effectiveDepth"),
            "d3DraftedTokens": d3_row.get("d3DraftedTokens"),
            "d3AcceptedTokens": d3_row.get("d3AcceptedTokens"),
            "mtpForwardPasses": d3_row.get("mtpForwardPasses"),
        },
    }


def d3_rows_by_label() -> dict[str, dict[str, Any]]:
    artifact = load_json(D3_MTP_ARTIFACT)
    rows: dict[str, dict[str, Any]] = {}
    for row in artifact.get("rows") or []:
        model = str(row.get("modelPath") or "").lower()
        if "27b" in model:
            rows["27b"] = row
        if "35b" in model:
            rows["35b"] = row
    return rows


def streaming_status(artifact: dict[str, Any]) -> dict[str, Any]:
    contracts = artifact.get("contracts") or {}
    required = [
        "chatCompletionsStreaming",
        "chatServiceContentDelta",
        "chatServiceReasoningDelta",
        "chatServiceToolCallDelta",
        "responsesStreamingEvents",
        "responsesPreviousResponseReuse",
        "responsesUsageCachedTokens",
        "qwenStreamingToolParser",
        "reasoningParserPerRequest",
    ]
    missing = [name for name in required if contracts.get(name) is not True]
    return {
        "status": "PASS" if artifact.get("ok") is True and not missing else "FAIL",
        "artifact": str(STREAMING_ARTIFACT.relative_to(ROOT)),
        "contractCount": artifact.get("contractCount"),
        "requiredContracts": required,
        "missingContracts": missing,
        "chatCompletionStreamFields": artifact.get("chatCompletionStreamFields"),
        "responsesStreamEvents": artifact.get("responsesStreamEvents"),
    }


def reasoning_status() -> dict[str, Any]:
    rows = []
    for label, path in REASONING_ARTIFACTS.items():
        artifact = load_json(path)
        status = artifact.get("status") or {}
        rows.append(
            {
                "label": label,
                "artifact": str(path.relative_to(ROOT)),
                "status": "PASS" if artifact.get("ok") is True and status.get("status") == "PASS_FINAL_ASSISTANT_CONTENT" else "FAIL",
                "assistantHasMarker": status.get("assistantHasMarker"),
                "thinkingHasMarker": status.get("thinkingHasMarker"),
                "warningShown": status.get("warningShown"),
            }
        )
    return {
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
    }


def cve_lookup_status(artifact: dict[str, Any]) -> dict[str, Any]:
    status = artifact.get("status") or {}
    return {
        "status": "PASS" if artifact.get("ok") is True
        and status.get("lookupCVEFirstTryArgumentPreserved") == "PASS"
        and status.get("finalAnswerMarker") == "PASS"
        and status.get("verboseToolTranscript") == "PASS"
        and artifact.get("toolSequence") == ["lookup_cve"]
        else "FAIL",
        "artifact": str(CVE_LOOKUP_ARTIFACT.relative_to(ROOT)),
        "targetCVE": artifact.get("targetCVE"),
        "toolSequence": artifact.get("toolSequence"),
        "componentStatus": status,
    }


def long_context_status(artifact: dict[str, Any]) -> dict[str, Any]:
    memory = artifact.get("memoryPreflight") or {}
    if artifact.get("ok") is True:
        status = "PASS"
    elif int(memory.get("heavyModelProcessCount") or 0) > 0:
        status = "BLOCKED_BY_HEAVY_MODEL_PROCESS"
    else:
        status = "FAIL"
    return {
        "status": status,
        "artifact": str(LONG_CONTEXT_ARTIFACT.relative_to(ROOT)),
        "actualPromptTokensByTokenizer": artifact.get("actualPromptTokensByTokenizer"),
        "sessionMaxPromptTokens": artifact.get("sessionMaxPromptTokens"),
        "memoryPreflight": memory,
    }


def main() -> None:
    d3_rows = d3_rows_by_label()
    model_rows = []
    for label, path in MODEL_ARTIFACTS.items():
        model_rows.append(
            evaluate_model(
                label,
                load_json(path),
                d3_rows.get(label),
                artifact_path=path.relative_to(ROOT),
            )
        )

    streaming = streaming_status(load_json(STREAMING_ARTIFACT))
    reasoning = reasoning_status()
    cve_lookup = cve_lookup_status(load_json(CVE_LOOKUP_ARTIFACT))
    long_context = long_context_status(load_json(LONG_CONTEXT_ARTIFACT))
    core_status = "PASS" if all(row["status"] == "PASS" for row in model_rows) and streaming["status"] == "PASS" and reasoning["status"] == "PASS" and cve_lookup["status"] == "PASS" else "FAIL"
    overall_status = core_status if long_context["status"] == "PASS" else "PARTIAL"

    report = {
        "ok": core_status == "PASS",
        "proofType": "qwen-runtime-readiness",
        "proofLevel": "existing-live-artifact-cache-parser-tool-streaming-d3-backed",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "coreStatus": core_status,
        "overallStatus": overall_status,
        "rows": model_rows,
        "statusCounts": {
            "PASS": sum(1 for row in model_rows if row["status"] == "PASS"),
            "FAIL": sum(1 for row in model_rows if row["status"] == "FAIL"),
        },
        "streaming": streaming,
        "reasoning": reasoning,
        "cveLookup": cve_lookup,
        "blockingEvidence": {
            "longContextStatus": long_context["status"],
            "longContext": long_context,
        },
        "sourceArtifacts": [
            str(path.relative_to(ROOT))
            for path in [
                *MODEL_ARTIFACTS.values(),
                *REASONING_ARTIFACTS.values(),
                D3_MTP_ARTIFACT,
                STREAMING_ARTIFACT,
                CVE_LOOKUP_ARTIFACT,
                LONG_CONTEXT_ARTIFACT,
            ]
        ],
    }
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if report["coreStatus"] != "PASS":
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(f"qwen runtime readiness proof wrote {DEFAULT_OUTPUT}")


if __name__ == "__main__":
    main()
