#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import stat
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
    requests: list[dict] = []


class MockEngineHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"status": "ok", "model": "mock-autopilot-policy"})
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
                {"choices": [{"delta": {"content": "Attempting blocked recon call."}}]},
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_blocked_nmap",
                                        "type": "function",
                                        "function": {"name": "nmap", "arguments": ""},
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
                                            "arguments": "{\"target\":\"127.0.0.1\",\"ports\":\"443\",\"service_detection\":true}"
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
                {"choices": [{"delta": {"content": "AUTOPILOT_POLICY_FINAL: nmap was blocked as requested."}}]},
                {"choices": [{"delta": {}}]},
            ]

        for event in events:
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
            self.wfile.flush()
            time.sleep(0.02)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def _json(self, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def request(method: str, path: str, body: dict | str | None = None, timeout: float = 8.0):
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


def install_fake_nmap(home: Path) -> None:
    tools_dir = home / ".exploitbot" / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    script = tools_dir / "nmap"
    script.write_text("#!/bin/sh\nprintf 'SHOULD_NOT_RUN\\n'\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def run() -> None:
    mock = ThreadingHTTPServer(("127.0.0.1", 18995), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-policy-home-")
    try:
        home = Path(temp_home.name)
        install_fake_nmap(home)

        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        coverage = request("GET", "/qa/agent-tool-authorization-coverage")
        autopilot = coverage.get("policies", {}).get("autopilot", {})
        if autopilot.get("explicitToolDeny") is not True:
            raise AssertionError(f"authorization coverage missing explicit deny: {coverage}")
        for expected in ("nmap", "sqlmap", "hydra", "metasploit", "sliver", "run_shell"):
            if expected not in autopilot.get("highRiskAutopilotTools", []):
                raise AssertionError(f"high-risk tool coverage missing {expected}: {coverage}")

        request("POST", "/engine/mock", MOCK_ENGINE)
        request("POST", "/mode", "autopilot")
        request("POST", "/send", "Do not use nmap. Explain whether the target is in scope without running recon.")

        messages = wait_until(
            lambda: (
                current if "nmap was explicitly disallowed by the latest user prompt." in json.dumps(current, sort_keys=True) else None
            ) if (current := request("GET", "/messages")) else None,
            "blocked nmap transcript",
            timeout=30.0,
        )
        message_text = json.dumps(messages, sort_keys=True)
        if "nmap was explicitly disallowed by the latest user prompt." not in message_text:
            raise AssertionError(f"nmap explicit-deny message missing: {messages}")
        if "SHOULD_NOT_RUN" in message_text:
            raise AssertionError(f"blocked nmap executable still ran: {messages}")

        final = wait_until(
            lambda: (
                current if "AUTOPILOT_POLICY_FINAL" in json.dumps(current, sort_keys=True) else None
            ) if (current := request("GET", "/messages")) else None,
            "post-block final answer",
            timeout=30.0,
        )
        if "AUTOPILOT_POLICY_FINAL" not in json.dumps(final, sort_keys=True):
            raise AssertionError(f"post-block final answer missing: {final}")

        print("autopilot-tool-policy proof passed")
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
        print(f"autopilot-tool-policy proof failed: {exc}", flush=True)
        raise SystemExit(1)
