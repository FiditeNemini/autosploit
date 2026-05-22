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


class MockHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(b'data: {"choices":[{"delta":{"content":"Audit proof complete."}}]}\n\n')
        self.wfile.write(b'data: {"usage":{"prompt_tokens":40,"completion_tokens":4,"prompt_tokens_details":{"cached_tokens":8}},"choices":[]}\n\n')
        self.wfile.write(b"data: [DONE]\n\n")


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


def wait_until(fn, label: str, timeout: float = 10.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = fn()
        if last:
            return last
        time.sleep(0.2)
    raise AssertionError(f"timed out waiting for {label}; last={last}")


def launch(env: dict[str, str]) -> subprocess.Popen:
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)
    if app.wait(timeout=30) != 0:
        raise RuntimeError("build_and_run --verify failed")
    wait_for_app()
    return app


def stop(app: subprocess.Popen | None) -> None:
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if app is not None and app.poll() is None:
        app.send_signal(signal.SIGTERM)


def assistant_audit(messages: list[dict]) -> dict:
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("contextSnippetCount", 0) > 0:
            return msg
    raise AssertionError(f"missing assistant request audit: {messages}")


def assert_audit() -> None:
    audit = assistant_audit(request("GET", "/messages"))
    if not 1 <= audit.get("contextSnippetCount", 0) <= 4:
        raise AssertionError(f"unexpected context snippet count: {audit}")
    if "Apache 2.4.49" not in audit.get("contextPreview", ""):
        raise AssertionError(f"missing context preview: {audit}")
    tools = audit.get("toolSchemas") or []
    if "search_context" not in tools or len(tools) > 12:
        raise AssertionError(f"unexpected tool schema audit: {audit}")


def run() -> None:
    mock = ThreadingHTTPServer(("127.0.0.1", 18992), MockHandler)
    thread = threading.Thread(target=mock.serve_forever, daemon=True)
    thread.start()
    with tempfile.TemporaryDirectory(prefix="exploitbot-audit-home-") as home:
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = home
        env["EXPLOITBOT_DATA_DIR"] = str(Path(home) / ".exploitbot" / "data")
        app: subprocess.Popen | None = None
        try:
            app = launch(env)
            request("POST", "/ops/create", "QA Request Audit|autopilot|192.0.2.0/24")
            request("POST", "/engine/mock", MOCK_ENGINE)
            request("POST", "/qa/seed-context")
            request("POST", "/send", "Audit Apache context and exposed tools")
            wait_until(
                lambda: request("GET", "/messages")
                if any("Audit proof complete" in m.get("content", "") for m in request("GET", "/messages"))
                else None,
                "audit assistant response",
            )
            assert_audit()
            request("POST", "/qa/save-current-messages")

            stop(app)
            app = launch(env)
            assert_audit()

            print("request-audit proof passed")
        finally:
            stop(app)
            mock.shutdown()


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"request-audit proof failed: {exc}", flush=True)
        raise SystemExit(1)
