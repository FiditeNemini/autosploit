#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
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
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-tool-schema-profile-exclusion.json"


class MockState:
    lock = threading.Lock()
    requests: list[dict[str, Any]] = []


class MockEngineHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"status": "ok", "model": "mock-excluded-run-shell"})
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
                {"choices": [{"delta": {"content": "Attempting a generic shell call that the active profile should block."}}]},
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_excluded_shell",
                                        "type": "function",
                                        "function": {"name": "run_shell", "arguments": ""},
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
                                        "function": {"arguments": json.dumps({"command": "printf SHOULD_NOT_RUN"})},
                                    }
                                ]
                            }
                        }
                    ]
                },
            ]
        else:
            events = [{"choices": [{"delta": {"content": "TOOL_SCHEMA_PROFILE_FINAL"}}]}]
        events.append({"usage": {"prompt_tokens": 120 + turn, "completion_tokens": 24}, "choices": [{"delta": {}}]})
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


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 8.0) -> Any:
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def wait_until(predicate, label: str, timeout: float = 30.0) -> Any:
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


def run() -> None:
    started = timestamp()
    mock_port = free_port()
    mock = ThreadingHTTPServer(("127.0.0.1", mock_port), MockEngineHandler)
    thread = threading.Thread(target=mock.serve_forever, daemon=True)
    thread.start()
    app: subprocess.Popen[str] | None = None
    try:
        with app_proof_lock("tool-schema-profile-exclusion-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            env = os.environ.copy()
            env["EXPLOITBOT_TESTING"] = "1"
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_until(lambda: request("GET", "/state", timeout=1.0), "app test server")

            base_url = f"http://127.0.0.1:{mock_port}"
            request("POST", "/engine/mock", base_url)
            request("POST", "/mode", "autopilot")
            request("POST", "/tab", "web")
            request(
                "POST",
                "/qa/apply-app-settings",
                {
                    "maxIterations": 2,
                    "toolSchemaMaxTools": 8,
                    "includeUnavailableToolSchemas": False,
                    "toolSchemaExcludedTools": ["run_shell"],
                    "forceFinalAnswerAfterToolResults": False,
                    "followAgent": False,
                },
            )
            catalog = request(
                "POST",
                "/qa/tool-catalog",
                {
                    "query": "Authorized loopback web scenario. Use dedicated web tools.",
                    "tab": "web",
                    "maxTools": 8,
                    "includeUnavailable": False,
                    "excludedToolNames": ["run_shell"],
                },
            )
            request("POST", "/send", "Authorized local fixture only. Use dedicated web tools and do not run shell.")
            wait_until(lambda: not request("GET", "/state").get("isWorking"), "chat turn completion", timeout=45.0)
            messages = request("GET", "/messages")
            state = request("GET", "/state")

        messages_text = json.dumps(messages, sort_keys=True)
        state_text = json.dumps(state, sort_keys=True)
        tool_names = catalog.get("toolNames") or []
        checks = {
            "catalogExcludedRunShell": "PASS" if "run_shell" not in tool_names else "FAIL",
            "stateRecordedExcludedTool": "PASS" if "run_shell" in ((state.get("chat") or {}).get("toolSchemaExcludedTools") or []) else "FAIL",
            "modelAttemptedExcludedTool": "PASS" if "Tool request: run_shell" in messages_text else "FAIL",
            "excludedToolBlocked": "PASS" if "excluded by the active tool schema profile" in messages_text else "FAIL",
            "excludedShellCommandNotExecuted": "PASS" if "SHOULD_NOT_RUN" not in state_text else "FAIL",
            "mockEngineOnly": "PASS" if state.get("model") == "mock-excluded-run-shell" or state.get("healthStatus") == "mock engine connected" else "FAIL",
        }
        ok = all(value == "PASS" for value in checks.values())
        report = {
            "ok": ok,
            "proofType": "tool-schema-profile-exclusion-live-app",
            "generatedAt": timestamp(),
            "startedAt": started,
            "finishedAt": timestamp(),
            "status": "PASS" if ok else "FAIL",
            "checks": checks,
            "catalog": catalog,
            "chat": state.get("chat") or {},
            "requestContext": state.get("requestContext") or {},
            "messageCount": len(messages),
            "messages": messages,
            "modelRequestToolNames": [
                ((tool.get("function") or {}).get("name") or "")
                for request_payload in MockState.requests
                for tool in (request_payload.get("tools") or [])
            ],
        }
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not ok:
            raise AssertionError(f"tool schema profile exclusion proof failed: {checks}")
        print(f"tool schema profile exclusion proof passed and wrote {ARTIFACT}")
    finally:
        mock.shutdown()
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app and app.poll() is None:
            app.terminate()


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"tool schema profile exclusion proof failed: {exc}", flush=True)
        raise SystemExit(1)
