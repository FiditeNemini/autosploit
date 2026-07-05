#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-individual-toolchain-coverage.json"

ARTIFACTS = [
    ROOT / "docs/live-proofs/2026-07-04-real-installed-tools-loopback.json",
    ROOT / "docs/live-proofs/2026-07-04-real-qwen-real-tools-loopback-27b.json",
    ROOT / "docs/live-proofs/2026-07-04-real-qwen-real-tools-loopback-35b.json",
    ROOT / "docs/live-proofs/2026-07-04-real-metasploit-safe-app.json",
    ROOT / "docs/live-proofs/2026-07-04-real-qwen-metasploit-safe-27b.json",
    ROOT / "docs/live-proofs/2026-07-04-real-qwen-metasploit-safe-35b.json",
    ROOT / "docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-27b.json",
    ROOT / "docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-35b.json",
]

TOOL_REQUIREMENTS = {
    "nmap": "real-loopback",
    "httpx": "real-loopback",
    "nuclei": "real-loopback",
    "hydra": "real-loopback",
    "netexec": "real-loopback",
    "linpeas": "real-loopback",
    "curl": "real-loopback-via-run-shell",
    "nc": "real-loopback-via-run-shell",
    "metasploit": "safe-version-command",
    "sqlmap": "autonomous-phase-loopback",
}


def load_artifacts() -> list[tuple[str, dict[str, Any]]]:
    loaded = []
    for path in ARTIFACTS:
        loaded.append((str(path.relative_to(ROOT)), json.loads(path.read_text(encoding="utf-8"))))
    return loaded


def text_blobs(value: Any) -> list[str]:
    blobs: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            blobs.extend(text_blobs(item))
    elif isinstance(value, list):
        for item in value:
            blobs.extend(text_blobs(item))
    elif isinstance(value, str):
        blobs.append(value)
    return blobs


def messages_for_tool(artifact: dict[str, Any], tool: str) -> list[dict[str, Any]]:
    rows = []
    for source in (artifact.get("messages") or []):
        if isinstance(source, dict):
            rows.append(source)
    for attempt in artifact.get("phaseAttempts") or []:
        if isinstance(attempt, dict):
            for source in attempt.get("messages") or []:
                if isinstance(source, dict):
                    rows.append(source)
    needle = tool.lower()
    matched = []
    for message in rows:
        message_tool = str(message.get("tool") or "").lower()
        content = str(message.get("content") or "").lower()
        if message_tool == needle or f"tool request: {needle}" in content:
            matched.append(message)
    return matched


def terminal_rows_for_tool(artifact: dict[str, Any], tool: str) -> list[dict[str, Any]]:
    rows = []
    states = [artifact.get("state")]
    for attempt in artifact.get("phaseAttempts") or []:
        if isinstance(attempt, dict):
            states.append(attempt.get("state"))
    needle = tool.lower()
    for state in states:
        if not isinstance(state, dict):
            continue
        terminal = state.get("terminal") if isinstance(state.get("terminal"), dict) else {}
        for row in terminal.get("commandTranscripts") or []:
            if not isinstance(row, dict):
                continue
            row_text = " ".join(str(row.get(key) or "") for key in ("tool", "command", "outputPreview")).lower()
            if needle in row_text:
                rows.append(row)
    return rows


def result_rows_for_tool(artifact: dict[str, Any], tool: str) -> list[dict[str, Any]]:
    rows = []
    states = [artifact.get("state")]
    for attempt in artifact.get("phaseAttempts") or []:
        if isinstance(attempt, dict):
            states.append(attempt.get("state"))
    needle = tool.lower()
    result_sets = [artifact.get("results")]
    for state in states:
        if isinstance(state, dict):
            result_sets.append(state.get("results"))
            tab_activities = state.get("tabActivities")
            if isinstance(tab_activities, dict):
                for row in tab_activities.values():
                    if isinstance(row, dict):
                        row_text = " ".join(
                            str(row.get(key) or "") for key in ("lastTool", "command", "outputPreview", "status")
                        ).lower()
                        if needle in row_text:
                            rows.append(row)
    for results in result_sets:
        if not isinstance(results, dict):
            continue
        for raw in results.get("rawResults") or []:
            if not isinstance(raw, dict):
                continue
            row_text = " ".join(str(raw.get(key) or "") for key in ("tool", "command", "outputPreview")).lower()
            if needle in row_text:
                rows.append(raw)
        for collection in ("ports", "web", "vulns", "creds", "network", "postAttribution"):
            for row in results.get(collection) or []:
                if not isinstance(row, dict):
                    continue
                row_text = " ".join(text_blobs(row)).lower()
                if needle in row_text:
                    rows.append(row)
    return rows


def qwen_models_for_tool(artifacts: list[tuple[str, dict[str, Any]]], tool: str) -> list[str]:
    models = []
    for _, artifact in artifacts:
        model = artifact.get("model")
        if not model or not isinstance(model, str):
            continue
        if tool in {"curl", "nc"} and run_shell_subtool_present(artifact, tool):
            models.append(model)
            continue
        if messages_for_tool(artifact, tool) and terminal_rows_for_tool(artifact, tool):
            models.append(model)
    return sorted(set(models))


def run_shell_subtool_present(artifact: dict[str, Any], subtool: str) -> bool:
    needle = f"tool={subtool}".lower()
    for message in artifact.get("messages") or []:
        if isinstance(message, dict) and needle in str(message.get("content") or "").lower():
            return True
    for row in result_rows_for_tool(artifact, "run_shell"):
        if needle in " ".join(text_blobs(row)).lower():
            return True
    return False


def build_tool_row(
    tool: str,
    artifacts: list[tuple[str, dict[str, Any]]],
    required_level: str,
) -> dict[str, Any]:
    evidence_paths: set[str] = set()
    chat = False
    terminal = False
    result_or_tab = False
    for artifact_path, artifact in artifacts:
        if artifact.get("ok") is not True:
            continue
        tool_chat = bool(messages_for_tool(artifact, tool))
        tool_terminal = bool(terminal_rows_for_tool(artifact, tool))
        tool_results = bool(result_rows_for_tool(artifact, tool))
        if tool in {"curl", "nc"}:
            tool_chat = tool_chat or run_shell_subtool_present(artifact, tool)
            tool_terminal = tool_terminal or run_shell_subtool_present(artifact, tool)
            tool_results = tool_results or run_shell_subtool_present(artifact, tool)
        if tool_chat or tool_terminal or tool_results:
            evidence_paths.add(artifact_path)
        chat = chat or tool_chat
        terminal = terminal or tool_terminal
        result_or_tab = result_or_tab or tool_results

    qwen_models = qwen_models_for_tool(artifacts, tool)
    status = "PASS" if chat and terminal and result_or_tab else "FAIL"
    return {
        "tool": tool,
        "status": status,
        "requiredLevel": required_level,
        "chatTranscript": chat,
        "terminalTranscript": terminal,
        "resultOrTabEvidence": result_or_tab,
        "qwenModelDrivenEvidence": qwen_models,
        "evidence": sorted(evidence_paths),
    }


def main() -> None:
    artifacts = load_artifacts()
    rows = [
        build_tool_row(tool, artifacts, required_level=level)
        for tool, level in TOOL_REQUIREMENTS.items()
    ]
    report = {
        "ok": all(row["status"] == "PASS" for row in rows),
        "proofType": "individual-toolchain-coverage",
        "proofLevel": "existing-live-artifact-per-tool-transcript-backed",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "toolCount": len(rows),
        "statusCounts": {
            "PASS": sum(1 for row in rows if row["status"] == "PASS"),
            "FAIL": sum(1 for row in rows if row["status"] == "FAIL"),
        },
        "rows": rows,
    }
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["ok"]:
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(f"individual toolchain coverage proof wrote {DEFAULT_OUTPUT}")


if __name__ == "__main__":
    main()
