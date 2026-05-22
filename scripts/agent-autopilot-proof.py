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
MOCK_ENGINE = "http://127.0.0.1:18992"


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
                {"choices": [{"delta": {"reasoning_content": "Agent should pull CVE context, then act in autopilot."}}]},
                {"choices": [{"delta": {"content": "Agent checking seeded Apache context."}}]},
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_agent_cve",
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
                        "prompt_tokens": 144,
                        "completion_tokens": 11,
                        "prompt_tokens_details": {"cached_tokens": 33},
                    },
                    "choices": [{"delta": {}}],
                },
            ]
        else:
            events = [
                {"choices": [{"delta": {"content": "Agent autopilot CVE lookup complete."}}]},
                {
                    "usage": {
                        "prompt_tokens": 166,
                        "completion_tokens": 7,
                        "prompt_tokens_details": {"cached_tokens": 55},
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


def wait_until(predicate, label: str, timeout: float = 24.0):
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
    mock = ThreadingHTTPServer(("127.0.0.1", 18992), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-agent-proof-home-")
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
        request("POST", "/qa/seed-context", "apache-2449")
        request("POST", "/qa/apply-app-settings", {
            "maxIterations": 6,
            "agents": {
                "multiAgentEnabled": True,
                "maxConcurrentAgents": 2,
            },
        })
        deployed = request("POST", "/qa/deploy-agent", {
            "name": "QA Web Agent",
            "task": "Use the context catalogue and check Apache risk as an autonomous agent",
            "type": "Web Vuln Agent",
        })
        if deployed.get("ok") is not True:
            raise AssertionError(f"agent deploy failed: {deployed}")

        state = wait_until(
            lambda: request("GET", "/state")
            if (request("GET", "/state").get("agents", {}).get("details") or [{}])[0].get("isComplete") is True
            else None,
            "agent autopilot completion",
            timeout=30.0,
        )
        agents = state.get("agents", {}).get("details") or []
        if len(agents) != 1:
            raise AssertionError(f"expected exactly one agent detail: {state}")
        agent = agents[0]
        if agent.get("interactionMode") != "autopilot":
            raise AssertionError(f"agent did not force autopilot mode: {agent}")
        if agent.get("baseURL") != MOCK_ENGINE:
            raise AssertionError(f"agent did not inherit mock engine URL: {agent}")
        if agent.get("modelName") != "mock-qwen-jang":
            raise AssertionError(f"agent did not inherit mock model: {agent}")
        if agent.get("useModelGenerationDefaults") is not True:
            raise AssertionError(f"agent did not preserve model generation defaults: {agent}")
        if agent.get("maxIterations") != 6:
            raise AssertionError(f"agent did not inherit loop limit: {agent}")
        if agent.get("messageCount", 0) < 3:
            raise AssertionError(f"agent message loop did not run: {agent}")
        if agent.get("toolCallCount", 0) < 1:
            raise AssertionError(f"agent autopilot did not execute tool call: {agent}")
        if agent.get("contextSnippetCount", 0) > 4:
            raise AssertionError(f"agent context packet was not bounded: {agent}")
        if agent.get("activeTab") != "web":
            raise AssertionError(f"agent typed prompt did not preserve web specialization: {agent}")
        if agent.get("hasTypePromptOverride") is not True:
            raise AssertionError(f"agent type prompt override was not preserved: {agent}")

        with MockState.lock:
            if len(MockState.requests) < 2:
                raise AssertionError(f"agent did not continue after tool call: {MockState.requests}")
            first_request = MockState.requests[0]
        request_text = json.dumps(first_request)
        for marker in ("Dynamic Context Catalogue", "Apache 2.4.49", "search_context"):
            if marker not in request_text:
                raise AssertionError(f"agent request missing {marker!r}: {request_text}")
        if first_request.get("enable_thinking") is not True:
            raise AssertionError(f"agent did not inherit reasoning setting: {first_request}")

        print("agent-autopilot proof passed")
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
        print(f"agent-autopilot proof failed: {exc}", flush=True)
        raise SystemExit(1)
