#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "docs/live-proofs/2026-07-04-tool-settings-real-inventory.json"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-05-all-installed-tools-smoke.json"

SAFE_SMOKE_ARGS = {
    "curl": ["--version"],
    "nc": ["-h"],
    "python3": ["--version"],
    "zsh": ["--version"],
    "subfinder": ["-version"],
    "dnsx": ["-version"],
    "nmap": ["--version"],
    "masscan": ["--version"],
    "httpx": ["-version"],
    "katana": ["-version"],
    "theHarvester": ["--help"],
    "nuclei": ["-version"],
    "sqlmap": ["--version"],
    "dalfox": ["version"],
    "feroxbuster": ["--version"],
    "ffuf": ["-V"],
    "arjun": ["--version"],
    "wpscan": ["--version"],
    "testssl": ["--version"],
    "graphqlmap": ["--help"],
    "jwt_tool": ["-h"],
    "netexec": ["--version"],
    "snmpwalk": ["-V"],
    "tshark": ["-v"],
    "bettercap": ["-version"],
    "chisel": ["--version"],
    "hashcat": ["--version"],
    "hydra": ["-h"],
    "haiti": ["--version"],
    "trufflehog": ["--version"],
    "syft": ["version"],
    "grype": ["version"],
    "osv_scanner": ["--version"],
    "semgrep": ["--version"],
    "bandit": ["--version"],
    "trivy": ["--version"],
    "checkov": ["--version"],
    "metasploit": ["-q", "-x", "version; exit"],
    "pwncat": ["--version"],
    "sliver": ["version"],
    "impacket": ["-h"],
    "linpeas": ["-h"],
    "sherlock": ["--version"],
    "holehe": ["--version"],
    "exiftool": ["-ver"],
    "gowitness": ["version"],
}

TIMEOUTS = {
    "metasploit": 45,
    "hashcat": 20,
    "wpscan": 20,
    "tshark": 20,
    "linpeas": 20,
}

OUTPUT_MARKERS = {
    "curl": ["curl"],
    "nc": ["usage", "netcat", "nc"],
    "python3": ["python"],
    "zsh": ["zsh"],
    "subfinder": ["subfinder", "current version"],
    "dnsx": ["dnsx", "current version"],
    "nmap": ["nmap"],
    "masscan": ["masscan"],
    "httpx": ["httpx", "current version"],
    "katana": ["katana", "current version"],
    "theHarvester": ["theharvester"],
    "nuclei": ["nuclei", "current version"],
    "sqlmap": ["sqlmap"],
    "dalfox": ["dalfox"],
    "feroxbuster": ["feroxbuster"],
    "ffuf": ["ffuf"],
    "arjun": ["arjun"],
    "wpscan": ["wpscan", "version"],
    "testssl": ["testssl"],
    "graphqlmap": ["graphqlmap", "usage"],
    "jwt_tool": ["jwt_tool", "usage"],
    "netexec": ["netexec", "nxc", "yippie-ki-yay"],
    "snmpwalk": ["snmpwalk", "net-snmp"],
    "tshark": ["tshark"],
    "bettercap": ["bettercap"],
    "chisel": ["chisel"],
    "hashcat": ["hashcat"],
    "hydra": ["hydra"],
    "haiti": ["haiti"],
    "trufflehog": ["trufflehog"],
    "syft": ["syft"],
    "grype": ["grype"],
    "osv_scanner": ["osv-scanner", "osv"],
    "semgrep": ["semgrep"],
    "bandit": ["bandit"],
    "trivy": ["trivy", "version"],
    "checkov": ["checkov"],
    "metasploit": ["framework", "console", "metasploit"],
    "pwncat": ["pwncat"],
    "sliver": ["sliver"],
    "impacket": ["secretsdump", "impacket"],
    "linpeas": ["linpeas", "peass"],
    "sherlock": ["sherlock"],
    "holehe": ["holehe"],
    "exiftool": ["exiftool", "12."],
    "gowitness": ["gowitness"],
}

FAIL_OUTPUT_MARKERS = [
    "traceback",
    "modulenotfounderror",
    "importerror",
    "sigsegv",
    "segmentation violation",
]


def tool_rows(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    settings = inventory.get("toolSettings") or {}
    rows = settings.get("tools") or []
    if not isinstance(rows, list):
        raise AssertionError("inventory toolSettings.tools is not a list")
    return [row for row in rows if isinstance(row, dict)]


def normalized_text(value: str) -> str:
    return value.replace("\x1b", "").lower()


def smoke_tool(row: dict[str, Any]) -> dict[str, Any]:
    name = str(row.get("name") or "")
    path = str(row.get("path") or "")
    status = str(row.get("status") or "")
    args = SAFE_SMOKE_ARGS.get(name)
    timeout = TIMEOUTS.get(name, 12)
    result: dict[str, Any] = {
        "tool": name,
        "category": row.get("category"),
        "installMethod": row.get("installMethod"),
        "inventoryStatus": status,
        "path": path,
        "args": args,
        "timeoutSeconds": timeout,
        "safeSmokeOnly": True,
        "externalTargetExecution": "not-started",
        "modelDrivenEvidence": "not-claimed",
    }
    if status != "installed":
        result.update({"status": "FAIL", "error": f"inventory status is {status!r}"})
        return result
    if not path:
        result.update({"status": "FAIL", "error": "installed tool has no path"})
        return result
    if args is None:
        result.update({"status": "FAIL", "error": "no safe smoke command configured"})
        return result
    try:
        completed = subprocess.run(
            [path, *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        lower = normalized_text(output)
        markers = OUTPUT_MARKERS.get(name, [name.lower()])
        failure_marker = next((marker for marker in FAIL_OUTPUT_MARKERS if marker in lower), None)
        marker_matched = any(marker.lower() in lower for marker in markers)
        usable = failure_marker is None and (completed.returncode == 0 or marker_matched)
        result.update(
            {
                "status": "PASS" if usable else "FAIL",
                "exitCode": completed.returncode,
                "failureMarker": failure_marker,
                "outputMarkerMatched": marker_matched,
                "outputPreview": output[:1200],
            }
        )
    except subprocess.TimeoutExpired as exc:
        result.update(
            {
                "status": "FAIL",
                "error": f"timeout after {timeout}s",
                "outputPreview": ((exc.stdout or "") + (exc.stderr or ""))[:1200],
            }
        )
    except Exception as exc:
        result.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    return result


def main() -> None:
    inventory = json.loads(DEFAULT_INVENTORY.read_text(encoding="utf-8"))
    rows = tool_rows(inventory)
    row_names = {str(row.get("name") or "") for row in rows}
    expected_names = set(SAFE_SMOKE_ARGS)
    missing_inventory_rows = sorted(expected_names - row_names)
    missing_configs = sorted(row_names - expected_names)
    if missing_inventory_rows or missing_configs:
        raise AssertionError(
            "installed-tool smoke registry mismatch: "
            f"missingInventoryRows={missing_inventory_rows} missingSmokeConfigs={missing_configs}"
        )

    smoke_rows = [smoke_tool(row) for row in rows]
    status_counts = {
        "PASS": sum(1 for row in smoke_rows if row.get("status") == "PASS"),
        "FAIL": sum(1 for row in smoke_rows if row.get("status") == "FAIL"),
    }
    report = {
        "ok": status_counts["FAIL"] == 0,
        "proofType": "all-installed-tools-smoke",
        "proofLevel": "current-machine-safe-executable-smoke-from-live-settings-inventory",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "inventoryEvidence": str(DEFAULT_INVENTORY.relative_to(ROOT)),
        "safeSmokeOnly": True,
        "externalTargetExecution": "not-started",
        "modelDrivenEvidence": "not-claimed",
        "toolCount": len(smoke_rows),
        "statusCounts": status_counts,
        "rows": smoke_rows,
    }
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["ok"]:
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(f"all-installed-tools-smoke proof passed and wrote {DEFAULT_OUTPUT}")


if __name__ == "__main__":
    main()
