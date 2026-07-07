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
MOCK_ENGINE = "http://127.0.0.1:19036"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-report-empty-generate-guard.json"
FINAL_MARKER = "REPORT_EMPTY_GENERATE_GUARD_FINAL"


class MockState:
    lock = threading.Lock()
    requests: list[dict[str, Any]] = []


class MockEngineHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"status": "ok", "model": "mock-report-empty-generate-guard"})
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
            events = [
                {"choices": [{"delta": {"content": "Attempting to render a report before evidence exists."}}]},
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_generate_empty_report",
                                        "type": "function",
                                        "function": {"name": "generate_report", "arguments": ""},
                                    }
                                ]
                            }
                        }
                    ]
                },
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "function": {"arguments": json.dumps({"template": "Full Report"})},
                                    }
                                ]
                            }
                        }
                    ]
                },
            ]
        else:
            events = [
                {
                    "choices": [
                        {
                            "delta": {
                                "content": (
                                    f"{FINAL_MARKER}: generate_report was refused because no confirmed "
                                    "findings existed."
                                )
                            }
                        }
                    ]
                }
            ]

        events.append(
            {
                "usage": {
                    "prompt_tokens": 180 + turn,
                    "completion_tokens": 32,
                    "prompt_tokens_details": {"cached_tokens": 8 * turn},
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
    transcript = json.dumps(messages, sort_keys=True)
    sequence = tool_sequence(messages)
    schema_names = model_schema_names(model_requests)
    report_render = state.get("reportRenderActions") or {}
    report_finding = state.get("reportFindingActions") or {}
    checks = {
        "modelInferenceStarted": passfail(len(model_requests) >= 2),
        "modelReceivedGenerateReportSchema": passfail("generate_report" in schema_names),
        "generateReportToolCalled": passfail(sequence[:1] == ["generate_report"]),
        "verboseToolTranscript": passfail("Tool request: generate_report" in transcript),
        "emptyReportRefused": passfail("Report not generated: no confirmed findings recorded" in transcript),
        "createFindingInstructionReturned": passfail("call create_finding first" in transcript),
        "noFindingRecorded": passfail((report_finding.get("findingCount") or 0) == 0),
        "reportPreviewNotRendered": passfail(report_render.get("status") != "done"),
        "finalAssistantReturned": passfail(FINAL_MARKER in transcript),
    }
    ok = all(value == "PASS" for value in checks.values())
    return {
        "ok": ok,
        "proofType": "report-empty-generate-guard-live",
        "proofLevel": "live-app-mock-engine-chat-callbacks-report-service",
        "status": "PASS" if ok else "FAIL",
        "startedAt": started_at,
        "finishedAt": finished_at,
        "generatedAt": finished_at,
        "toolSequence": sequence,
        "toolSchemaNames": sorted(set(schema_names)),
        "checks": checks,
        "reportRenderActions": report_render,
        "reportFindingActions": report_finding,
        "messages": messages,
        "notes": [
            "Mock engine is deterministic; this proves the real Swift app chat loop refuses generate_report when no FindingService findings exist.",
            "No local model is loaded in this proof; real-Qwen natural tool choice remains a separate live proof boundary.",
        ],
    }


def run() -> None:
    started_at = timestamp()
    mock = ThreadingHTTPServer(("127.0.0.1", 19036), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()
    app: subprocess.Popen[str] | None = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-report-empty-home-", ignore_cleanup_errors=True)
    report: dict[str, Any] = {"ok": False, "proofType": "report-empty-generate-guard-live", "startedAt": started_at}
    error: Exception | None = None
    try:
        home = Path(temp_home.name)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")

        with app_proof_lock("report-empty-generate-guard-proof.py"):
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
                {"toolSchemaMaxTools": 16, "maxIterations": 3, "forceFinalAnswerAfterToolResults": True},
            )
            request(
                "POST",
                "/send",
                (
                    "Authorized local report callback guard test only. Try generate_report before any finding "
                    f"exists, then explain the refusal and end with {FINAL_MARKER}."
                ),
            )

            messages = wait_until(
                lambda: (
                    current
                    if any(m.get("role") == "assistant" and FINAL_MARKER in str(m.get("content") or "") for m in current)
                    else None
                )
                if (current := request("GET", "/messages"))
                else None,
                "empty report guard final answer",
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
                raise AssertionError("empty report guard checks failed", report["checks"])
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
    print(f"report empty-generate guard proof passed: {ARTIFACT}")


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"report empty-generate guard proof failed: {exc}", flush=True)
        raise SystemExit(1)
