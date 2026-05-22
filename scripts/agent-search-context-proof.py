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


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
MOCK_ENGINE = "http://127.0.0.1:18993"


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
                {"choices": [{"delta": {"content": "Agent pulling parsed post context."}}]},
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_agent_context",
                                        "type": "function",
                                        "function": {
                                            "name": "search_context",
                                            "arguments": "",
                                        },
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
                                            "arguments": "{\"query\":\"linpeas qa-linux-01 www-data privilege escalation attribution\",\"max_snippets\":4}"
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                },
                {
                    "usage": {
                        "prompt_tokens": 180,
                        "completion_tokens": 12,
                        "prompt_tokens_details": {"cached_tokens": 44},
                    },
                    "choices": [{"delta": {}}],
                },
            ]
        else:
            request_text = json.dumps(payload)
            content = "Agent found parsed post attribution." if "qa-linux-01" in request_text and "www-data" in request_text else "Agent did not see parsed post attribution."
            events = [
                {"choices": [{"delta": {"content": content}}]},
                {
                    "usage": {
                        "prompt_tokens": 220,
                        "completion_tokens": 8,
                        "prompt_tokens_details": {"cached_tokens": 66},
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


def request(method: str, path: str, body: str | dict | None = None, timeout: float = 8.0):
    if isinstance(body, dict):
        body = json.dumps(body)
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


def wait_until(predicate, label: str, timeout: float = 30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            value = predicate()
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            value = None
        if value:
            return value
        time.sleep(0.25)
    raise AssertionError(f"timed out waiting for {label}")


def run() -> None:
    mock = ThreadingHTTPServer(("127.0.0.1", 18993), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-agent-context-home-")
    try:
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = temp_home.name
        env["EXPLOITBOT_DATA_DIR"] = str(Path(temp_home.name) / ".exploitbot" / "data")
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        request("POST", "/engine/mock", MOCK_ENGINE)
        seeded = request("POST", "/qa/seed-result-parser-fixture")
        if seeded.get("ok") is not True:
            raise AssertionError(f"result parser fixture seed failed: {seeded}")
        request("POST", "/qa/apply-app-settings", {
            "maxIterations": 6,
            "context": {
                "enabled": True,
                "maxSnippets": 4,
                "includeAssets": True,
                "includeFindings": True,
                "includeRecentToolOutput": True,
                "includeStash": False,
                "cveMode": "off",
            },
            "agents": {
                "multiAgentEnabled": True,
                "maxConcurrentAgents": 2,
            },
        })
        deployed = request("POST", "/qa/deploy-agent", {
            "name": "QA Context Agent",
            "task": "Use search_context to inspect parsed post-exploitation attribution.",
            "type": "Custom Agent",
        })
        if deployed.get("ok") is not True:
            raise AssertionError(f"agent deploy failed: {deployed}")

        state = wait_until(
            lambda: request("GET", "/state")
            if (request("GET", "/state").get("agents", {}).get("details") or [{}])[0].get("isComplete") is True
            else None,
            "agent search_context completion",
        )
        agent = (state.get("agents", {}).get("details") or [{}])[0]
        if agent.get("interactionMode") != "autopilot":
            raise AssertionError(f"agent did not force autopilot: {agent}")
        if agent.get("toolCallCount", 0) < 1:
            raise AssertionError(f"agent did not execute search_context tool: {agent}")
        if "search_context" not in agent.get("toolSchemas", []):
            raise AssertionError(f"agent was not exposed search_context schema: {agent}")

        tool_outputs = "\n".join(
            item.get("content", "")
            for item in agent.get("toolOutputs", [])
            if item.get("tool") == "search_context"
        )
        for marker in ("[post.attribution]", "qa-linux-01", "www-data", "linpeas-host"):
            if marker not in tool_outputs:
                raise AssertionError(f"agent search_context output missing {marker!r}: {agent}")

        with MockState.lock:
            if len(MockState.requests) < 2:
                raise AssertionError(f"agent did not continue after search_context: {MockState.requests}")
            second_request = json.dumps(MockState.requests[1])
        for marker in ("qa-linux-01", "www-data", "post.attribution"):
            if marker not in second_request:
                raise AssertionError(f"search_context result was not sent back to model: {second_request}")

        print("agent-search-context proof passed")
    finally:
        mock.shutdown()
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
        temp_home.cleanup()


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"agent-search-context proof failed: {exc}", flush=True)
        raise SystemExit(1)
