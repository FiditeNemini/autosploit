#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TOOL_INSTALLER = ROOT / "ExploitBot/Sources/ExploitBot/Services/ToolInstaller.swift"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-nuclei-app-managed-install.json"
NUCLEI_PACKAGE = "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdoutPreview": proc.stdout[:1200],
        "stderrPreview": proc.stderr[:1200],
    }


def nuclei_tooldef_line() -> str:
    text = TOOL_INSTALLER.read_text(encoding="utf-8")
    for line in text.splitlines():
        if 'ToolDef(name: "nuclei"' in line:
            return line.strip()
    return ""


def build_report() -> dict[str, Any]:
    line = nuclei_tooldef_line()
    binary = Path.home() / ".exploitbot" / "tools" / "nuclei"
    version = run([str(binary), "-version"]) if binary.exists() else None
    source_status = (
        "PASS"
        if 'mkdir -p "$HOME/.exploitbot/tools"' in line
        and 'GOBIN="$HOME/.exploitbot/tools" go install -v' in line
        and NUCLEI_PACKAGE in line
        else "FAIL"
    )
    binary_status = "PASS" if binary.exists() and binary.is_file() else "FAIL"
    version_text = ""
    if version:
        version_text = f"{version.get('stdoutPreview', '')}\n{version.get('stderrPreview', '')}"
    version_status = (
        "PASS"
        if version and version.get("returncode") == 0 and "Nuclei Engine Version" in version_text
        else "FAIL"
    )
    overall = "PASS" if source_status == binary_status == version_status == "PASS" else "FAIL"
    return {
        "generatedAt": timestamp(),
        "proofType": "nuclei-app-managed-install",
        "source": "ExploitBot/Sources/ExploitBot/Services/ToolInstaller.swift",
        "package": NUCLEI_PACKAGE,
        "status": {
            "sourceUsesAppManagedGoBin": source_status,
            "appManagedBinaryPresent": binary_status,
            "appManagedBinaryVersionRuns": version_status,
            "overall": overall,
        },
        "sourceLine": line,
        "binaryPath": str(binary),
        "versionCommand": version,
        "boundary": "Verifies installer command shape plus current-machine app-managed nuclei binary/version only; no target scan is run.",
    }


def main() -> None:
    report = build_report()
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"nuclei app-managed install proof wrote {ARTIFACT} overall={report['status']['overall']}")
    raise SystemExit(0 if report["status"]["overall"] == "PASS" else 1)


if __name__ == "__main__":
    main()
