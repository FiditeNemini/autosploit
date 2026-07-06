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
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-impacket-cli-mapping.json"


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=30.0)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdoutPreview": proc.stdout[:2000],
        "stderrPreview": proc.stderr[:2000],
    }


def impacket_build_case() -> str:
    text = TOOL_DEFINITIONS.read_text(encoding="utf-8")
    cli_builder = text[text.index("static func buildCliArgs"):]
    case = cli_builder[cli_builder.index('case "impacket":'):]
    return case[: case.index('case "linpeas":')]


def build_report() -> dict[str, Any]:
    case = impacket_build_case()
    module_help = run(["python3", "-m", "impacket.examples.secretsdump", "-h"])
    script_path = shutil.which("secretsdump.py")
    script_help = run([script_path or "secretsdump.py", "-h"]) if script_path else {"returncode": 127}
    status = {
        "sourceUsesConsoleScript": (
            "PASS"
            if 'let scriptBinary = script.hasSuffix(".py") ? script : "\\(script).py"' in case
            and 'return (scriptBinary, [arguments["target"] as? String ?? ""])' in case
            else "FAIL"
        ),
        "sourceAvoidsPythonModulePath": (
            "PASS" if 'python3", ["-m", "impacket.examples.' not in case else "FAIL"
        ),
        "consoleScriptPresent": "PASS" if script_path else "FAIL",
        "consoleScriptHelpRuns": "PASS" if script_help.get("returncode") == 0 else "FAIL",
        "pythonModulePathFailsHere": "PASS" if module_help.get("returncode") != 0 else "FAIL",
    }
    status["overall"] = "PASS" if all(value == "PASS" for value in status.values()) else "FAIL"
    return {
        "ok": status["overall"] == "PASS",
        "proofType": "impacket-cli-mapping",
        "proofLevel": "source-plus-current-machine-help-command",
        "generatedAt": timestamp(),
        "source": "ExploitBot/Sources/ExploitBot/Services/ToolDefinitions.swift",
        "status": status,
        "scriptPath": script_path,
        "scriptHelp": script_help,
        "moduleHelp": module_help,
        "boundary": "Runs help commands only; does not execute impacket against a target.",
    }


def main() -> None:
    report = build_report()
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["ok"]:
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(f"impacket CLI mapping proof passed: {ARTIFACT}")


if __name__ == "__main__":
    main()
