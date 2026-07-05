#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
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
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-real-metasploit-safe-app.json"


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:6000]
        raise AssertionError(message + suffix)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 12.0):
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def wait_until(predicate, label: str, timeout: float = 90.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = predicate()
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            last = None
        if last:
            return last
        time.sleep(0.5)
    raise AssertionError(f"timed out waiting for {label}: {last}")


def wait_for_assistant_marker(marker: str, timeout: float = 120.0):
    def ready():
        messages = request("GET", "/messages", timeout=3.0)
        state = request("GET", "/state", timeout=3.0)
        assistant_has_marker = any(
            msg.get("role") == "assistant" and marker in str(msg.get("content") or "")
            for msg in messages
        )
        if assistant_has_marker and not state.get("isWorking") and not state.get("isStreaming"):
            return messages
        return None

    return wait_until(ready, f"assistant marker {marker}", timeout=timeout)


def command_path(name: str) -> str | None:
    found = subprocess.run(["/bin/sh", "-lc", f"command -v {name}"], text=True, capture_output=True)
    path = found.stdout.strip()
    return path or None


def msf_version(path: str) -> str:
    result = subprocess.run([path, "-q", "-x", "version; exit"], text=True, capture_output=True, timeout=45)
    output = result.stdout + result.stderr
    require(result.returncode == 0, "msfconsole version command failed", output)
    match = re.search(r"Framework:\s*([^\n]+)", output)
    return match.group(1).strip() if match else ""


class MockState:
    lock = threading.Lock()
    requests: list[dict[str, Any]] = []


class MockEngineHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"status": "ok", "model": "mock-real-metasploit-safe"})
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
                {"choices": [{"delta": {"content": "Checking real Metasploit availability through the app tool loop."}}]},
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 0,
                                "id": "call_real_metasploit_version",
                                "type": "function",
                                "function": {"name": "metasploit", "arguments": ""},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 0,
                                "function": {"arguments": json.dumps({"command": "version; exit"})},
                            }]
                        }
                    }]
                },
                {"choices": [{"finish_reason": "tool_calls", "delta": {}}]},
            ]
        else:
            events = [
                {"choices": [{"delta": {"content": "REAL_METASPLOIT_SAFE_FINAL: real msfconsole version output was captured through chat, terminal transcripts, and raw results."}}]},
                {"choices": [{"finish_reason": "stop", "delta": {}}]},
            ]

        for event in events:
            line = f"data: {json.dumps(event)}\n\n".encode("utf-8")
            self.wfile.write(line)
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def _json(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_app_bundle() -> None:
    result = subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT)
    require(result.returncode == 0, "build_and_run --build-only failed")
    require(APP_BINARY.exists(), f"app binary missing after build: {APP_BINARY}")


def run() -> None:
    output = Path(os.environ.get("EXPLOITBOT_REAL_METASPLOIT_SAFE_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    msf_path = command_path("msfconsole")
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "real-metasploit-safe-app",
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "msfconsolePath": msf_path,
    }
    error: Exception | None = None
    app: subprocess.Popen[str] | None = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-real-metasploit-safe-home-")
    server_port = free_port()
    server = ThreadingHTTPServer(("127.0.0.1", server_port), MockEngineHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    mock_engine = f"http://127.0.0.1:{server_port}"
    try:
        require(msf_path is not None, "msfconsole is missing from PATH")
        report["directMsfVersion"] = msf_version(msf_path)

        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = temp_home.name
        env["EXPLOITBOT_DATA_DIR"] = str(Path(temp_home.name) / ".exploitbot" / "data")
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        build_app_bundle()
        app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
        wait_until(lambda: request("GET", "/state", timeout=1.0), "app test server")

        request("POST", "/engine/mock", mock_engine)
        request("POST", "/mode", "autopilot")
        request("POST", "/tab", "exploit")
        request("POST", "/reasoning", "off")
        request(
            "POST",
            "/qa/apply-app-settings",
            {
                "maxIterations": 3,
                "forceFinalAnswerAfterToolResults": False,
                "toolSchemaMaxTools": 32,
                "includeUnavailableToolSchemas": False,
                "chat": {"enableReasoning": False},
            },
        )
        catalog = request(
            "POST",
            "/qa/tool-catalog",
            {
                "query": "Authorized safe local Metasploit version check. Use metasploit only for version; exit.",
                "tab": "exploit",
                "maxTools": 32,
                "includeUnavailable": False,
            },
        )
        require("metasploit" in (catalog.get("toolNames") or []), "metasploit schema missing despite installed msfconsole", catalog)
        report["preflightToolCatalog"] = catalog

        request("POST", "/send", "Authorized local-only proof. Use metasploit with command `version; exit`, then return REAL_METASPLOIT_SAFE_FINAL.")
        messages = wait_for_assistant_marker("REAL_METASPLOIT_SAFE_FINAL", timeout=120.0)
        state = request("GET", "/state", timeout=8.0)
        results = request("GET", "/results", timeout=8.0)

        messages_text = json.dumps(messages, sort_keys=True)
        terminal_text = json.dumps((state.get("terminal") or {}).get("commandTranscripts") or [], sort_keys=True)
        results_text = json.dumps(results, sort_keys=True)
        for marker in ("Tool request: metasploit", "msfconsole", "version; exit", "Framework:", "Console  :", "REAL_METASPLOIT_SAFE_FINAL"):
            require(marker in messages_text, f"chat transcript missing {marker!r}", messages)
        for marker in ("metasploit", "msfconsole", "version; exit", "Framework:", "Console  :"):
            require(marker in terminal_text, f"terminal commandTranscripts missing {marker!r}", state.get("terminal"))
        for marker in ("Framework:", "Console  :"):
            require(marker in results_text, f"raw results missing {marker!r}", results)

        report.update(
            {
                "ok": True,
                "messages": messages,
                "state": state,
                "results": results,
                "chatContainsMetasploitOutput": "Framework:" in messages_text,
                "terminalContainsMetasploitOutput": "Framework:" in terminal_text,
                "resultsContainMetasploitOutput": "Framework:" in results_text,
                "status": {
                    "realMetasploitSafeAppExecution": "PASS",
                    "verboseChatToolOutput": "PASS",
                    "terminalTranscriptOutput": "PASS",
                    "rawResultsOutput": "PASS",
                },
            }
        )
    except Exception as exc:
        error = exc
        report.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        try:
            report["messages"] = request("GET", "/messages", timeout=3.0)
            report["state"] = request("GET", "/state", timeout=3.0)
        except Exception:
            pass
    finally:
        server.shutdown()
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
        temp_home.cleanup()
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error is not None:
        raise error
    print("real-metasploit-safe-app proof passed")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"real-metasploit-safe-app proof failed: {exc}", flush=True)
        raise SystemExit(1)
