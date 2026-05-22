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
MOCK_ENGINE = "http://127.0.0.1:18994"


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
                {"choices": [{"delta": {"content": "Running service scan."}}]},
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_nmap_fanout",
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
                {
                    "usage": {
                        "prompt_tokens": 160,
                        "completion_tokens": 10,
                        "prompt_tokens_details": {"cached_tokens": 22},
                    },
                    "choices": [{"delta": {}}],
                },
            ]
        else:
            events = [
                {"choices": [{"delta": {"content": "Service scan complete."}}]},
                {
                    "usage": {
                        "prompt_tokens": 190,
                        "completion_tokens": 5,
                        "prompt_tokens_details": {"cached_tokens": 48},
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
    while time.time() < deadline:
        try:
            value = predicate()
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            value = None
        if value:
            return value
        time.sleep(0.25)
    raise AssertionError(f"timed out waiting for {label}")


def wait_for_recon_done(timeout: float = 30.0):
    deadline = time.time() + timeout
    last_state = None
    while time.time() < deadline:
        try:
            last_state = request("GET", "/state")
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            time.sleep(0.25)
            continue
        if last_state.get("tabActivities", {}).get("recon", {}).get("status") == "done":
            return last_state
        time.sleep(0.25)
    messages = request("GET", "/messages")
    raise AssertionError(f"timed out waiting for nmap fanout completion: state={last_state} messages={messages}")


def install_fake_nmap(home: Path) -> Path:
    tools_dir = home / ".exploitbot" / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    script = tools_dir / "nmap"
    script.write_text("#!/bin/sh\nprintf '443/tcp open https Apache httpd 2.4.49\\n'\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return tools_dir


def run() -> None:
    mock = ThreadingHTTPServer(("127.0.0.1", 18994), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-fanout-home-")
    try:
        home = Path(temp_home.name)
        tools_dir = install_fake_nmap(home)

        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        env["PATH"] = f"{tools_dir}:{env.get('PATH', '/usr/bin:/bin')}"
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        request("POST", "/engine/mock", MOCK_ENGINE)
        request("POST", "/mode", "autopilot")
        request("POST", "/tab", "web")
        request("POST", "/send", "Run nmap service detection for 127.0.0.1:443 and summarize the result.")

        state = wait_for_recon_done()
        messages = request("GET", "/messages")
        results = request("GET", "/results")

        if not any(msg.get("tool") == "nmap" and "443/tcp open https Apache" in msg.get("content", "") for msg in messages):
            raise AssertionError(f"nmap tool chat card missing parsed output: {messages}")
        if not any(port.get("port") == 443 and port.get("service") == "https" and "Apache" in port.get("version", "") for port in results.get("ports", [])):
            raise AssertionError(f"nmap output did not parse into /results ports: {results}")

        recon = state.get("tabActivities", {}).get("recon", {})
        if recon.get("lastTool") != "nmap" or recon.get("status") != "done" or recon.get("count", 0) < 1:
            raise AssertionError(f"recon tab activity did not reflect nmap completion: {state}")
        if state.get("activeTab") != "recon":
            raise AssertionError(f"tool auto-tab did not switch to recon: {state}")
        if state.get("tools", 0) < 1:
            raise AssertionError(f"phase tool counter did not increment: {state}")

        feed_text = "\n".join(entry.get("text", "") for entry in state.get("feedRecent", []))
        for marker in ("Running nmap", "nmap: 1 lines output"):
            if marker not in feed_text:
                raise AssertionError(f"activity feed missing {marker!r}: {state}")

        packet = request("POST", "/qa/context-packet", {
            "query": "Apache 2.4.49 443 https",
            "maxSnippets": 4,
            "includeAssets": True,
            "includeFindings": False,
            "includeRecentToolOutput": True,
            "includeStash": False,
            "cveMode": "off",
        })["packet"]
        for marker in ("443/tcp", "Apache httpd 2.4.49"):
            if marker not in packet:
                raise AssertionError(f"context packet missing {marker!r}: {packet}")

        print("tool-fanout-status proof passed")
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
        print(f"tool-fanout-status proof failed: {exc}", flush=True)
        raise SystemExit(1)
