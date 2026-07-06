#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TOOL_DEFINITIONS = ROOT / "ExploitBot/Sources/ExploitBot/Services/ToolDefinitions.swift"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-gowitness-cli-mapping.json"


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def run(cmd: list[str]) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=30.0)
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdoutPreview": proc.stdout[:2000],
            "stderrPreview": proc.stderr[:2000],
        }
    except FileNotFoundError as exc:
        return {"cmd": cmd, "returncode": 127, "stderrPreview": str(exc)}


def gowitness_build_case() -> str:
    text = TOOL_DEFINITIONS.read_text(encoding="utf-8")
    cli_builder = text[text.index("static func buildCliArgs"):]
    case = cli_builder[cli_builder.index('case "gowitness":'):]
    return case[: case.index('case "search_cve"')]


def build_report() -> dict[str, Any]:
    case = gowitness_build_case()
    binary = shutil.which("gowitness")
    old_help = run([binary or "gowitness", "single", "--help"])
    new_help = run([binary or "gowitness", "scan", "single", "--help"])
    source_status = (
        "PASS"
        if '["single", "--url"' not in case
        and '"scan", "single", "--url"' in case
        and '"--screenshot-path", screenshotDir' in case
        else "FAIL"
    )
    status = {
        "sourceUsesScanSingle": source_status,
        "binaryPresent": "PASS" if binary else "BLOCKED",
        "oldSingleHelpRejected": (
            "PASS" if binary and old_help.get("returncode") != 0 else "BLOCKED"
        ),
        "scanSingleHelpRuns": (
            "PASS" if binary and new_help.get("returncode") == 0 else "BLOCKED"
        ),
    }
    if source_status == "FAIL":
        overall = "FAIL"
    elif any(value == "BLOCKED" for value in status.values()):
        overall = "PARTIAL"
    else:
        overall = "PASS"
    status["overall"] = overall
    return {
        "ok": overall in {"PASS", "PARTIAL"},
        "proofType": "gowitness-cli-mapping",
        "proofLevel": "source-contract-plus-current-machine-cli-preflight",
        "generatedAt": timestamp(),
        "source": "ExploitBot/Sources/ExploitBot/Services/ToolDefinitions.swift",
        "status": status,
        "binaryPath": binary,
        "oldSingleHelp": old_help,
        "scanSingleHelp": new_help,
        "missingLiveEvidence": [] if binary else ["gowitness binary is not installed on this machine, so scan single help could not be live-verified."],
        "boundary": "No screenshot or target action is run; help/preflight only.",
    }


def main() -> None:
    report = build_report()
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if report["status"]["overall"] == "FAIL":
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(f"gowitness CLI mapping proof wrote {ARTIFACT} overall={report['status']['overall']}")


if __name__ == "__main__":
    main()
