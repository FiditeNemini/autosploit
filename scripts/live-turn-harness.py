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

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        if turn == 1 or "Suggest the next Apache check" in user_text or "Ask approval before checking Apache" in user_text:
            events = [
                {"choices": [{"delta": {"reasoning_content": "Need context, then query CVEs."}}]},
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
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
            self.wfile.flush()
            time.sleep(0.05)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

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
