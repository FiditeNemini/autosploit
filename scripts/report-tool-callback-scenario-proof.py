#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
MOCK_ENGINE = "http://127.0.0.1:19032"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-report-tool-callback-scenario.json"
FINAL_MARKER = "REPORT_TOOL_CALLBACK_FINAL"
EXPECTED_TOOLS = ["create_finding", "generate_report", "export_report"]


class MockState:
    lock = threading.Lock()
    requests: list[dict[str, Any]] = []


class MockEngineHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"status": "ok", "model": "mock-report-tool-callback"})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        with MockState.lock:
            MockState.requests.append(payload)
            turn = len(MockState.requests)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        if turn == 1:
            events = [{"choices": [{"delta": {"content": "Recording confirmed finding and generating report."}}]}]
            tool_calls = [
                (
                    "call_create_finding",
                    "create_finding",
                    {
                        "title": "SQL injection in local search parameter",
                        "severity": "high",
                        "target": "http://127.0.0.1:19032/search?q=1",
                        "description": "Confirmed SQL injection in q parameter using local fixture evidence.",
                        "evidence": "Parameter: q (GET)\nEXPLOITBOT_SQLI_PROOF_USER=alice",
                        "attack_chain": "Discover /search?q=1; Run sqlmap; Confirm EXPLOITBOT_SQLI_PROOF_USER=alice",
                        "impact": "An attacker can alter query logic and extract application data.",
                        "remediation": "Use parameterized queries and add regression coverage.",
                        "cve": "CVE-2021-41773",
                        "vuln_type": "sql_injection",
                        "cvss": 8.1,
                    },
                ),
                ("call_generate_report", "generate_report", {"template": "Full Report"}),
                ("call_export_report", "export_report", {"template": "Full Report", "action": "export_report"}),
            ]
            for index, (call_id, name, arguments) in enumerate(tool_calls):
                events.append(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": index,
                                            "id": call_id,
                                            "type": "function",
                                            "function": {"name": name, "arguments": ""},
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                )
                events.append(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": index,
                                            "function": {"arguments": json.dumps(arguments, sort_keys=True)},
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                )
        else:
            events = [
                {
                    "choices": [
                        {
                            "delta": {
                                "content": (
                                    f"{FINAL_MARKER}: create_finding recorded the proof-bearing SQLi finding, "
                                    "generate_report rendered it, and export_report produced report artifacts."
                                )
                            }
                        }
                    ]
                }
            ]

        events.append(
            {
                "usage": {
                    "prompt_tokens": 280 + turn,
                    "completion_tokens": 64,
                    "prompt_tokens_details": {"cached_tokens": 16 * turn},
                },
                "choices": [{"delta": {}}],
            }
        )
        for event in events:
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
            self.wfile.flush()
            time.sleep(0.02)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def _json(self, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def passfail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def request(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 8.0):
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def wait_until(predicate, label: str, timeout: float = 90.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = predicate()
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            last = None
        if last:
            return last
        time.sleep(0.25)
    raise AssertionError(f"timed out waiting for {label}: {last}")


def build_app_bundle() -> None:
    result = subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError("build_and_run --build-only failed")
    if not APP_BINARY.exists():
        raise RuntimeError(f"app binary missing after build: {APP_BINARY}")


def tool_sequence(messages: list[dict[str, Any]]) -> list[str]:
    sequence: list[str] = []
    for message in messages:
        if message.get("role") == "toolCall":
            tool = str(message.get("tool") or "").strip()
            if tool:
                sequence.append(tool)
    return sequence


def model_schema_names(model_requests: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for request_payload in model_requests:
        for tool in request_payload.get("tools") or []:
            name = ((tool.get("function") or {}).get("name") or "").strip()
            if name:
                names.append(name)
    return names


def write_report(report: dict[str, Any]) -> None:
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_report(
    *,
    started_at: str,
    finished_at: str,
    messages: list[dict[str, Any]],
    state: dict[str, Any],
    model_requests: list[dict[str, Any]],
) -> dict[str, Any]:
    text = json.dumps(messages, sort_keys=True)
    state_text = json.dumps(state, sort_keys=True)
    sequence = tool_sequence(messages)
    schema_names = model_schema_names(model_requests)
    report_export = state.get("reportExport") or {}
    report_render = state.get("reportRenderActions") or {}
    report_finding = state.get("reportFindingActions") or {}
    artifact_rows = report_export.get("artifacts") or []
    checks = {
        "modelInferenceStarted": passfail(len(model_requests) >= 2),
        "modelReceivedReportToolSchemas": passfail(all(tool in schema_names for tool in EXPECTED_TOOLS)),
        "reportToolSequence": passfail(sequence[:3] == EXPECTED_TOOLS),
        "verboseToolTranscript": passfail(all(f"Tool request: {tool}" in text for tool in EXPECTED_TOOLS)),
        "createFindingCallbackResult": passfail("Finding recorded:" in text and report_finding.get("findingCount") == 1),
        "generateReportCallbackResult": passfail("Report generated:" in text and report_render.get("status") == "done"),
        "exportReportCallbackResult": passfail("Report exported:" in text and report_export.get("status") == "done"),
        "reportContainsEvidence": passfail(
            "SQL injection in local search parameter" in state_text
            and "EXPLOITBOT_SQLI_PROOF_USER=alice" in state_text
            and "Parameter: q (GET)" in state_text
        ),
        "reportArtifactsPresent": passfail(
            len(artifact_rows) == 4
            and all(row.get("exists") is True and row.get("bytes", 0) > 0 for row in artifact_rows)
        ),
    }
    ok = all(value == "PASS" for value in checks.values())
    return {
        "ok": ok,
        "proofType": "report-tool-callback-scenario-live",
        "proofLevel": "live-app-mock-engine-chat-callbacks-report-service",
        "status": "PASS" if ok else "FAIL",
        "startedAt": started_at,
        "finishedAt": finished_at,
        "generatedAt": finished_at,
        "expectedTools": EXPECTED_TOOLS,
        "toolSequence": sequence,
        "toolSchemaNames": sorted(set(schema_names)),
        "checks": checks,
        "reportRenderActions": report_render,
        "reportFindingActions": report_finding,
        "reportExport": report_export,
        "messages": messages,
        "notes": [
            "Mock engine is deterministic; this proves the real Swift app chat loop, callback handlers, FindingService, ReportService preview, and ReportService export path.",
            "No local model is loaded in this proof; real-Qwen natural report-tool selection is a separate live proof boundary.",
        ],
    }


def run() -> None:
    started_at = timestamp()
    mock = ThreadingHTTPServer(("127.0.0.1", 19032), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()
    app: subprocess.Popen[str] | None = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-report-tool-home-", ignore_cleanup_errors=True)
    report: dict[str, Any] = {"ok": False, "proofType": "report-tool-callback-scenario-live", "startedAt": started_at}
    error: Exception | None = None
    try:
        home = Path(temp_home.name)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")

        with app_proof_lock("report-tool-callback-scenario-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_until(lambda: request("GET", "/state", timeout=1.0), "app test server")

            request("POST", "/engine/mock", MOCK_ENGINE)
            request("POST", "/mode", "autopilot")
            request("POST", "/reasoning", "off")
            request("POST", "/tab", "report")
            request(
                "POST",
                "/qa/apply-app-settings",
                {"toolSchemaMaxTools": 16, "maxIterations": 4, "forceFinalAnswerAfterToolResults": True},
            )
            request(
                "POST",
                "/send",
                (
                    "Authorized local report callback test only. Use create_finding with the provided proof, "
                    "then generate_report, then export_report. End with REPORT_TOOL_CALLBACK_FINAL."
                ),
            )

            messages = wait_until(
                lambda: (
                    current if any(m.get("role") == "assistant" and FINAL_MARKER in str(m.get("content") or "") for m in current) else None
                ) if (current := request("GET", "/messages")) else None,
                "report callback final answer",
            )
            state = request("GET", "/state")
            with MockState.lock:
                model_requests = list(MockState.requests)
            report = build_report(
                started_at=started_at,
                finished_at=timestamp(),
                messages=messages,
                state=state,
                model_requests=model_requests,
            )
            if not report["ok"]:
                raise AssertionError("report tool callback scenario checks failed", report["checks"])
    except Exception as exc:
        error = exc
        report.update({"ok": False, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}", "finishedAt": timestamp()})
        try:
            report["messages"] = request("GET", "/messages", timeout=5.0)
            report["state"] = request("GET", "/state", timeout=5.0)
        except Exception:
            pass
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
        mock.shutdown()
        temp_home.cleanup()
        write_report(report)

    if error is not None:
        raise error
    print(f"report-tool-callback scenario proof passed: {ARTIFACT}")


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"report-tool-callback scenario proof failed: {exc}", flush=True)
        raise SystemExit(1)
