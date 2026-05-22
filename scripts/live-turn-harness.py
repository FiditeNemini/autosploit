#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
MOCK_ENGINE = "http://127.0.0.1:18991"


class MockState:
    lock = threading.Lock()
    requests: list[dict] = []


class MockEngineHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"status": "ok", "model": "mock-qwen-jang"})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(body)
        with MockState.lock:
            MockState.requests.append(payload)
            turn = len(MockState.requests)
        user_text = "\n".join(
            str(message.get("content", ""))
            for message in payload.get("messages", [])
            if message.get("role") == "user"
        )
        thinking_enabled = bool(payload.get("enable_thinking"))

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        if "Slow stream for cancel" in user_text:
            events = [
                {"choices": [{"delta": {"content": "slow-start "}}]},
                {"choices": [{"delta": {"content": "slow-middle "}}]},
                {"choices": [{"delta": {"content": "slow-final-marker"}}]},
            ]
        elif "Run cancellable shell tool" in user_text:
            events = [
                {"choices": [{"delta": {"content": "Starting cancellable shell proof."}}]},
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_cancel_shell",
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
                                        "function": {
                                            "arguments": "{\"command\":\"printf tool-start; sleep 10; printf tool-final-marker\"}"
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                },
            ]
        elif turn == 1 or "Suggest the next Apache check" in user_text or "Ask approval before checking Apache" in user_text:
            events = [
                {"choices": [{"delta": {"content": "I will check the seeded service context."}}]},
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {"name": "search_cve", "arguments": ""},
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
                                        "function": {
                                            "arguments": "{\"query\":\"Apache 2.4.49\",\"max_results\":3}"
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                },
                {
                    "usage": {
                        "prompt_tokens": 123,
                        "completion_tokens": 9,
                        "prompt_tokens_details": {"cached_tokens": 42},
                    },
                    "choices": [{"delta": {}}],
                },
            ]
            if thinking_enabled:
                events.insert(0, {"choices": [{"delta": {"reasoning_content": "Need context, then query CVEs."}}]})
        else:
            events = [
                {"choices": [{"delta": {"content": "CVE lookup complete. Document the finding."}}]},
                {
                    "usage": {
                        "prompt_tokens": 156,
                        "completion_tokens": 7,
                        "prompt_tokens_details": {"cached_tokens": 88},
                    },
                    "choices": [{"delta": {}}],
                },
            ]

        for event in events:
            try:
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
            time.sleep(0.4 if "Slow stream for cancel" in user_text else 0.05)
        try:
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def _json(self, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def request(method: str, path: str, body: str | None = None, timeout: float = 8.0):
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def wait_for_app(timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            request("GET", "/state", timeout=1.0)
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"app test server did not become ready: {last_error}")


def wait_until(predicate, label: str, timeout: float = 12.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.25)
    raise AssertionError(f"timed out waiting for {label}")


def latest_request() -> dict:
    with MockState.lock:
        if not MockState.requests:
            raise AssertionError("mock engine did not receive any requests")
        return MockState.requests[-1]


def assert_contains(haystack: str, needle: str, label: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"missing {label}: expected {needle!r} in {haystack!r}")


def run() -> None:
    mock = ThreadingHTTPServer(("127.0.0.1", 18991), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        request("POST", "/engine/mock", MOCK_ENGINE)
        request("POST", "/qa/seed-context", "apache-2449")
        request("POST", "/mode", "autopilot")
        request("POST", "/reasoning", "on")
        request("POST", "/send", "Use the context catalogue and check Apache risk")

        messages = wait_until(
            lambda: request("GET", "/messages") if len(request("GET", "/messages")) >= 4 else None,
            "autopilot chat/tool loop",
        )
        joined = "\n".join(m["content"] for m in messages)
        assert_contains(joined, "CVE lookup complete", "second streamed assistant response")
        assert any(m.get("tool") == "search_cve" and "ok" in m.get("status", "") for m in messages), messages

        state = request("GET", "/state")
        assert state["metrics"]["tokPerSec"] > 0, state
        assert state["metrics"]["ttft"] > 0, state

        with MockState.lock:
            first_request = MockState.requests[0]
        request_text = json.dumps(first_request)
        assert_contains(request_text, "Dynamic Context Catalogue", "dynamic context packet")
        assert_contains(request_text, "Apache 2.4.49", "seeded context")
        assert first_request["enable_thinking"] is True
        assert first_request["tools"], "tools schema was not sent"

        request("POST", "/clear")
        request("POST", "/mode", "manual")
        request("POST", "/send", "Suggest the next Apache check")
        manual_messages = wait_until(
            lambda: request("GET", "/messages") if any("Manual mode" in m["content"] for m in request("GET", "/messages")) else None,
            "manual suggested tool call",
        )
        assert any("Manual mode" in m["content"] and m.get("tool") == "search_cve" for m in manual_messages), manual_messages

        request("POST", "/clear")
        request("POST", "/mode", "copilot")
        request("POST", "/send", "Ask approval before checking Apache")
        wait_until(
            lambda: request("GET", "/messages") if any(m["role"] == "approval" for m in request("GET", "/messages")) else None,
            "copilot approval card",
        )
        request("POST", "/approve")
        copilot_messages = wait_until(
            lambda: request("GET", "/messages") if any(m.get("tool") == "search_cve" for m in request("GET", "/messages")) else None,
            "copilot approved tool execution",
        )
        assert any(m.get("tool") == "search_cve" for m in copilot_messages), copilot_messages

        request("POST", "/clear")
        request("POST", "/mode", "autopilot")
        request("POST", "/reasoning", "off")
        request("POST", "/send", "No reasoning path Apache check")
        no_reasoning_messages = wait_until(
            lambda: request("GET", "/messages") if any("CVE lookup complete" in m["content"] for m in request("GET", "/messages")) else None,
            "reasoning-off streamed response",
        )
        assert all(m["role"] != "thinking" for m in no_reasoning_messages), no_reasoning_messages
        no_reasoning_request = latest_request()
        assert no_reasoning_request["enable_thinking"] is False, no_reasoning_request
        assert no_reasoning_request["chat_template_kwargs"]["enable_thinking"] is False, no_reasoning_request

        request("POST", "/clear")
        request("POST", "/reasoning", "on")
        request("POST", "/send", "Slow stream for cancel")
        wait_until(
            lambda: request("GET", "/state") if request("GET", "/state").get("isStreaming") else None,
            "slow stream start",
        )
        request("POST", "/stop")
        stopped_state = wait_until(
            lambda: request("GET", "/state") if not request("GET", "/state").get("isWorking") else None,
            "stream cancellation",
        )
        stopped_messages = request("GET", "/messages")
        stopped_joined = "\n".join(m["content"] for m in stopped_messages)
        assert not stopped_state["isStreaming"], stopped_state
        if "slow-final-marker" in stopped_joined:
            raise AssertionError(f"stop did not interrupt slow stream: {stopped_messages}")

        request("POST", "/clear")
        request("POST", "/mode", "autopilot")
        request("POST", "/send", "Run cancellable shell tool")
        wait_until(
            lambda: request("GET", "/state") if request("GET", "/state").get("toolExecutor", {}).get("isRunning") else None,
            "long-running shell tool start",
        )
        request("POST", "/stop")
        wait_until(
            lambda: request("GET", "/state") if not request("GET", "/state").get("isWorking") else None,
            "tool cancellation",
        )
        tool_cancel_messages = request("GET", "/messages")
        shell_cards = [m for m in tool_cancel_messages if m.get("tool") == "run_shell"]
        if not shell_cards:
            raise AssertionError(f"missing run_shell tool card: {tool_cancel_messages}")
        latest_shell = shell_cards[-1]
        assert "canceled" in latest_shell.get("status", ""), tool_cancel_messages
        shell_output = latest_shell["content"].split("\n", 1)[1] if "\n" in latest_shell["content"] else latest_shell["content"]
        if "tool-final-marker" in shell_output:
            raise AssertionError(f"stop did not interrupt shell tool: {latest_shell}")

        print("live-turn harness passed")
    finally:
        mock.shutdown()
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError) as exc:
        print(f"live-turn harness failed: {exc}", file=sys.stderr)
        sys.exit(1)
