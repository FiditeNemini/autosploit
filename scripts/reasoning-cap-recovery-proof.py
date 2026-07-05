#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHAT_SERVICE = ROOT / "ExploitBot/Sources/ExploitBot/Services/ChatService.swift"
LEGACY_512 = ROOT / "docs/live-proofs/2026-07-04-real-qwen-27b-reasoning-on.json"
LIVE_27B_1024 = ROOT / "docs/live-proofs/2026-07-04-real-qwen-27b-reasoning-on-1024.json"
LIVE_35B_1024 = ROOT / "docs/live-proofs/2026-07-04-real-qwen-35b-reasoning-on-1024.json"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-reasoning-cap-recovery.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:4000]
        raise AssertionError(message + suffix)


def main() -> None:
    source = CHAT_SERVICE.read_text(encoding="utf-8")
    legacy = load(LEGACY_512)
    live_27b = load(LIVE_27B_1024)
    live_35b = load(LIVE_35B_1024)

    source_checks = {
        "namesCurrentCap": "Current Max Tokens: \\(maxTokens)" in source,
        "names1024Recovery": "1024-token Qwen live proofs produced final assistant content" in source,
        "doesNotChangeSettings": "This warning does not change generation settings" in source,
        "warningPathStillTriggered": "reasoningOnlyLengthWarning(maxTokens: maxTokens)" in source,
    }
    live_1024_rows = []
    for label, artifact in (("27b", live_27b), ("35b", live_35b)):
        status = artifact.get("status") or {}
        live_1024_rows.append(
            {
                "label": label,
                "artifact": str((LIVE_27B_1024 if label == "27b" else LIVE_35B_1024).relative_to(ROOT)),
                "ok": artifact.get("ok") is True,
                "status": status.get("status"),
                "maxTokens": artifact.get("maxTokens"),
                "assistantHasMarker": status.get("assistantHasMarker"),
                "thinkingHasMarker": status.get("thinkingHasMarker"),
                "warningShown": status.get("warningShown"),
            }
        )

    legacy_status = legacy.get("status") or {}
    legacy_warning_ok = (
        legacy.get("ok") is False
        and legacy.get("maxTokens") == 512
        and legacy_status.get("warningShown") is True
        and legacy_status.get("thinkingHasMarker") is True
    )
    live_1024_ok = all(
        row["ok"] is True
        and row["status"] == "PASS_FINAL_ASSISTANT_CONTENT"
        and row["maxTokens"] == 1024
        and row["assistantHasMarker"] is True
        and row["thinkingHasMarker"] is False
        and row["warningShown"] is False
        for row in live_1024_rows
    )
    source_ok = all(source_checks.values())

    report = {
        "ok": source_ok and live_1024_ok and legacy_warning_ok,
        "proofType": "reasoning-cap-recovery",
        "proofLevel": "source-warning-contract-plus-existing-live-qwen-artifacts",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sourceWarningStatus": "PASS" if source_ok else "FAIL",
        "live1024Status": "PASS" if live_1024_ok else "FAIL",
        "legacy512Status": "PASS_WARNING_ARTIFACT" if legacy_warning_ok else "FAIL",
        "doesNotChangeGenerationSettings": source_checks["doesNotChangeSettings"],
        "recommendedRecoveryMaxTokens": 1024,
        "sourceChecks": source_checks,
        "legacy512": {
            "artifact": str(LEGACY_512.relative_to(ROOT)),
            "ok": legacy.get("ok"),
            "status": legacy_status.get("status"),
            "maxTokens": legacy.get("maxTokens"),
            "warningShown": legacy_status.get("warningShown"),
            "thinkingHasMarker": legacy_status.get("thinkingHasMarker"),
        },
        "live1024Rows": live_1024_rows,
        "sourceArtifacts": [
            str(CHAT_SERVICE.relative_to(ROOT)),
            str(LEGACY_512.relative_to(ROOT)),
            str(LIVE_27B_1024.relative_to(ROOT)),
            str(LIVE_35B_1024.relative_to(ROOT)),
        ],
        "blockedLiveRefresh": "Skipped fresh low-cap model rerun while unrelated 35B eval remains active; this proof preserves existing live model artifacts and current source/build evidence.",
    }
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    require(report["ok"] is True, "reasoning cap recovery proof failed", report)
    print(f"reasoning cap recovery proof wrote {DEFAULT_OUTPUT}")


if __name__ == "__main__":
    main()
