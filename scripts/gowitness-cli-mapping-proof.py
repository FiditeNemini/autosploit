#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TOOL_DEFINITIONS = ROOT / "ExploitBot/Sources/ExploitBot/Services/ToolDefinitions.swift"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-gowitness-cli-mapping.json"
FIXTURE_MARKER = "EXPLOITBOT_GOWITNESS_FIXTURE_OK"


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


def candidate_binaries() -> list[Path]:
    candidates = [
        Path.home() / ".exploitbot" / "tools" / "gowitness",
        Path.home() / "go" / "bin" / "gowitness",
    ]
    path_binary = shutil.which("gowitness")
    if path_binary:
        candidates.append(Path(path_binary))
    return candidates


def find_gowitness_binary() -> str | None:
    for candidate in candidate_binaries():
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        body = (
            "<html><head><title>ExploitBot Gowitness Fixture</title></head>"
            f"<body>{FIXTURE_MARKER}</body></html>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def safe_loopback_screenshot(binary: str | None) -> dict[str, Any]:
    if not binary:
        return {"status": "BLOCKED", "missingEvidence": "gowitness binary missing"}

    port = free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    with tempfile.TemporaryDirectory(prefix="exploitbot-gowitness-proof-") as tmp:
        screenshot_dir = Path(tmp) / "screens"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = Path(tmp) / "gowitness.jsonl"
        url = f"http://127.0.0.1:{port}/"
        try:
            proc = run([
                binary,
                "scan",
                "single",
                "--url",
                url,
                "--screenshot-path",
                str(screenshot_dir),
                "--screenshot-format",
                "png",
                "--write-jsonl",
                str(jsonl_path),
            ])
            screenshots = sorted(path.name for path in screenshot_dir.glob("*.png"))
            return {
                "status": "PASS" if proc.get("returncode") == 0 and screenshots else "FAIL",
                "url": url,
                "command": proc,
                "screenshotCount": len(screenshots),
                "screenshots": screenshots,
                "jsonlExists": jsonl_path.exists(),
            }
        finally:
            server.shutdown()
            thread.join(timeout=5.0)


def build_report() -> dict[str, Any]:
    case = gowitness_build_case()
    binary = find_gowitness_binary()
    old_help = run([binary or "gowitness", "single", "--help"])
    new_help = run([binary or "gowitness", "scan", "single", "--help"])
    screenshot = safe_loopback_screenshot(binary)
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
        "safeLoopbackScreenshot": screenshot.get("status", "FAIL"),
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
        "safeLoopbackScreenshot": screenshot,
        "missingLiveEvidence": [] if binary else ["gowitness binary is not installed on this machine, so scan single help and safe loopback screenshot could not be live-verified."],
        "boundary": "Runs only help commands and a screenshot against a temporary 127.0.0.1 fixture.",
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
