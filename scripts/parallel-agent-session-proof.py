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
MOCK_ENGINE = "http://127.0.0.1:18994"


class MockState:
    lock = threading.Lock()
    requests: list[dict] = []
    starts: list[float] = []
    ends: list[float] = []
    in_flight = 0
    max_in_flight = 0


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
        now = time.time()
        with MockState.lock:
            MockState.requests.append(payload)
            MockState.starts.append(now)
            MockState.in_flight += 1
            MockState.max_in_flight = max(MockState.max_in_flight, MockState.in_flight)
            turn = len(MockState.requests)

        try:
            time.sleep(1.25)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()

            events = [
                {"choices": [{"delta": {"reasoning_content": f"Parallel agent {turn} planning authorized test steps."}}]},
                {"choices": [{"delta": {"content": f"Parallel agent {turn} completed its scoped check."}}]},
                {
                    "usage": {
                        "prompt_tokens": 120 + turn,
                        "completion_tokens": 9,
                        "prompt_tokens_details": {"cached_tokens": 30 + turn},
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
        finally:
            with MockState.lock:
                MockState.in_flight -= 1
                MockState.ends.append(time.time())

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
    last_value = None
    while time.time() < deadline:
        try:
            last_value = predicate()
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            last_value = None
        if last_value:
            return last_value
        time.sleep(0.2)
    raise AssertionError(f"timed out waiting for {label}; last={last_value}")


def run() -> None:
    mock = ThreadingHTTPServer(("127.0.0.1", 18994), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-parallel-agent-home-")
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
            "maxIterations": 1,
            "agents": {
                "multiAgentEnabled": True,
                "maxConcurrentAgents": 2,
            },
            "chat": {
                "enableReasoning": True,
            },
        })

        first = request("POST", "/qa/deploy-agent", {
            "name": "QA Parallel Recon",
            "task": "Run an authorized recon-only check against 192.0.2.10 and report status.",
            "type": "Recon Agent",
        })
        second = request("POST", "/qa/deploy-agent", {
            "name": "QA Parallel Web",
            "task": "Run an authorized web-only check against 192.0.2.10 and report status.",
            "type": "Web Vuln Agent",
        })
        if first.get("ok") is not True or second.get("ok") is not True:
            raise AssertionError(f"parallel agent deploy failed: first={first} second={second}")

        progress = wait_until(
            lambda: request("GET", "/state")
            if (request("GET", "/state").get("agents") or {}).get("workingCount", 0) >= 2
            else None,
            "two agents working concurrently",
            timeout=8.0,
        )
        agents = progress.get("agents") or {}
        details = agents.get("details") or []
        if agents.get("activeAgents") != 2:
            raise AssertionError(f"expected two active agents: {agents}")
        if agents.get("maxConcurrentAgents") != 2:
            raise AssertionError(f"max concurrent agent setting not applied: {agents}")
        if agents.get("workingCount", 0) < 2:
            raise AssertionError(f"workingCount did not expose live parallel progress: {agents}")
        if len(details) != 2:
            raise AssertionError(f"agent details missing: {agents}")
        for agent in details:
            if agent.get("toolSchemaMaxTools", 0) <= 12:
                raise AssertionError(f"agent did not inherit full tool schema access: {agent}")
            if agent.get("isWorking") is not True:
                raise AssertionError(f"agent detail did not expose working status: {agent}")
            if not agent.get("statusLine"):
                raise AssertionError(f"agent detail missing status line: {agent}")

        finished = wait_until(
            lambda: request("GET", "/state")
            if all(item.get("isComplete") for item in (request("GET", "/state").get("agents") or {}).get("details") or [])
            else None,
            "parallel agents complete",
            timeout=30.0,
        )
        finished_agents = finished.get("agents") or {}
        finished_details = finished_agents.get("details") or []
        if len(finished_details) != 2:
            raise AssertionError(f"finished state lost agents: {finished_agents}")
        if finished_agents.get("workingCount") != 0:
            raise AssertionError(f"agents still marked working after completion: {finished_agents}")
        for agent in finished_details:
            if agent.get("messageCount", 0) < 2:
                raise AssertionError(f"agent did not complete a chat turn: {agent}")
            if agent.get("isComplete") is not True:
                raise AssertionError(f"agent not marked complete: {agent}")

        with MockState.lock:
            max_in_flight = MockState.max_in_flight
            request_count = len(MockState.requests)
            starts = list(MockState.starts)
            ends = list(MockState.ends)
        if request_count < 2:
            raise AssertionError(f"mock engine saw too few requests: {request_count}")
        if max_in_flight < 2:
            raise AssertionError(f"mock engine did not observe overlapping agent requests: max_in_flight={max_in_flight} starts={starts} ends={ends}")

        names = [item.get("name") for item in finished_details]
        print(f"parallel-agent-session proof passed: agents={names} max_in_flight={max_in_flight}")
    finally:
        mock.shutdown()
        mock.server_close()
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
        temp_home.cleanup()


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"parallel-agent-session proof failed: {exc}", flush=True)
        raise SystemExit(1)
