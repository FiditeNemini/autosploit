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
MOCK_ENGINE = "http://127.0.0.1:18995"


class MockState:
    lock = threading.Lock()
    request_count = 0


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
        self.rfile.read(length)
        with MockState.lock:
            MockState.request_count += 1
            turn = MockState.request_count

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        if turn == 1:
            events = [
                {"choices": [{"delta": {"content": "Running live status probe."}}]},
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_agent_live_status",
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
                                            "arguments": "{\"command\":\"sleep 3; echo AGENT_LIVE_STATUS_DONE\"}"
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                },
                {"choices": [{"delta": {}}]},
            ]
        else:
            events = [
                {"choices": [{"delta": {"content": "Live tool status complete."}}]},
                {"choices": [{"delta": {}}]},
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


def wait_until(predicate, label: str, timeout: float = 15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            value = predicate()
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            value = None
        if value:
            return value
        time.sleep(0.2)
    raise AssertionError(f"timed out waiting for {label}")


def first_agent(state: dict) -> dict:
    details = ((state.get("agents") or {}).get("details") or [])
    return details[0] if details else {}


def run() -> None:
    mock = ThreadingHTTPServer(("127.0.0.1", 18995), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-agent-live-status-")
    app = None
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
        request("POST", "/qa/apply-app-settings", {
            "maxIterations": 3,
            "agents": {"multiAgentEnabled": True, "maxConcurrentAgents": 2},
        })
        deployed = request("POST", "/qa/deploy-agent", {
            "name": "QA Live Status Agent",
            "task": "Run the live status probe",
            "type": "Supply Chain Agent",
        })
        if deployed.get("ok") is not True:
            raise AssertionError(f"agent deploy failed: {deployed}")

        running_state = wait_until(
            lambda: request("GET", "/state")
            if any(
                output.get("tool") == "run_shell" and output.get("status") == "running..."
                for output in first_agent(request("GET", "/state")).get("toolOutputs", [])
            )
            else None,
            "agent run_shell running status",
        )
        agent = first_agent(running_state)
        if agent.get("currentToolName") != "run_shell":
            raise AssertionError(f"agent current tool name missing while running: {agent}")
        if agent.get("currentToolStatus") != "running...":
            raise AssertionError(f"agent current tool status missing while running: {agent}")
        if "sleep 3" not in (agent.get("currentToolPreview") or ""):
            raise AssertionError(f"agent current tool preview missing command: {agent}")
        if agent.get("runningToolCount") != 1:
            raise AssertionError(f"agent running tool count mismatch: {agent}")
        if "run_shell" not in (agent.get("statusLine") or ""):
            raise AssertionError(f"agent status line does not name live tool: {agent}")

        complete_state = wait_until(
            lambda: request("GET", "/state")
            if first_agent(request("GET", "/state")).get("isComplete") is True
            else None,
            "agent completion",
            timeout=20.0,
        )
        complete_agent = first_agent(complete_state)
        if complete_agent.get("lastToolName") != "run_shell":
            raise AssertionError(f"agent last tool not retained after completion: {complete_agent}")
        if not str(complete_agent.get("lastToolStatus") or "").startswith("ok "):
            raise AssertionError(f"agent last tool status not retained after completion: {complete_agent}")
        if "AGENT_LIVE_STATUS_DONE" not in (complete_agent.get("lastToolPreview") or ""):
            raise AssertionError(f"agent last tool preview missing output: {complete_agent}")

        print("agent-live-tool-status proof passed")
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
        print(f"agent-live-tool-status proof failed: {exc}", flush=True)
        raise SystemExit(1)
