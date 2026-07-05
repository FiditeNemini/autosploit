#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ATTEMPT = ROOT / "docs/live-proofs/2026-07-04-real-qwen-near-max-context-27b.json"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-near-max-context-runtime-attempt-summary.json"


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def regex_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def build_report(attempt: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    log = attempt.get("engineLogTail") or ""
    lower = attempt.get("lowerCapRejectResponse") or {}
    lower_error = ((lower.get("json") or {}).get("error") or {}) if isinstance(lower, dict) else {}
    lower_message = str(lower_error.get("message") or "")
    prompt_tokens = int(attempt.get("actualPromptTokensByTokenizer") or 0)
    runtime_seq_len = regex_int(r"seq_len=(\d+)", log)
    timeout_seconds = regex_int(r"--timeout\s+(\d+)", log)
    target_preflight = attempt.get("targetMemoryPreflight") or {}
    memory_preflight = attempt.get("memoryPreflight") or {}
    stop_reason = os.environ.get("EXPLOITBOT_NEAR_MAX_ATTEMPT_STOP_REASON", "")

    status = {
        "targetMemoryPreflight": "PASS" if target_preflight.get("targetRequiredAvailableGB") == 80.0 else "FAIL",
        "modelLoadMemoryPreflight": "PASS" if memory_preflight.get("requiredAvailableGB") == 42.0 else "FAIL",
        "exactLowerCapRejection": (
            "PASS"
            if lower.get("status") == 413 and str(prompt_tokens) in lower_message.replace(",", "")
            else "FAIL"
        ),
        "serverTimeoutForwarded": "PASS" if timeout_seconds == 3600 else "FAIL",
        "chunkedPrefillEntered": "PASS" if runtime_seq_len and "Enabling chunked prefill" in log else "FAIL",
        "finalGenerationCompleted": "PASS" if attempt.get("ok") is True else "FAIL",
    }

    return {
        "ok": status["finalGenerationCompleted"] == "PASS",
        "proofType": "near-max-context-runtime-attempt-summary",
        "proofLevel": "live-near-max-attempt-artifact-and-engine-log-backed",
        "generatedAt": generated_at or timestamp(),
        "attemptArtifact": str(ATTEMPT.relative_to(ROOT)),
        "attemptStartedAt": attempt.get("startedAt"),
        "attemptFinishedAt": attempt.get("finishedAt"),
        "model": attempt.get("model"),
        "targetPromptTokens": attempt.get("targetPromptTokens"),
        "actualPromptTokensByTokenizer": prompt_tokens,
        "sessionMaxPromptTokens": attempt.get("sessionMaxPromptTokens"),
        "runtimeSeqLen": runtime_seq_len,
        "serverTimeoutSeconds": timeout_seconds,
        "targetMemoryPreflight": target_preflight,
        "modelLoadMemoryPreflight": memory_preflight,
        "lowerCapRejectResponse": lower,
        "chunkedPrefillEvidence": {
            "entered": "Enabling chunked prefill" in log,
            "oneShotBufferMessagePresent": "one-shot attention buffer" in log,
            "clientDisconnected": "Client disconnected" in log,
        },
        "operatorStopReason": stop_reason,
        "status": status,
        "missingEvidence": (
            "The 258k-token request reached Qwen chunked prefill but did not complete "
            "a final assistant response or post-generation cache write proof."
        ),
    }


def main() -> None:
    attempt = json.loads(ATTEMPT.read_text(encoding="utf-8"))
    output = Path(os.environ.get("EXPLOITBOT_NEAR_MAX_ATTEMPT_SUMMARY_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    report = build_report(attempt)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["ok"]:
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(f"near-max context attempt summary proof wrote {output}")


if __name__ == "__main__":
    main()
