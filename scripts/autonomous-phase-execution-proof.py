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
MOCK_ENGINE = "http://127.0.0.1:18996"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"


class MockState:
    lock = threading.Lock()
    requests: list[dict] = []


TOOL_CALLS = [
    ("call_phase_nmap", "nmap", {"target": "127.0.0.1", "ports": "443", "service_detection": True}),
    ("call_phase_netexec", "netexec", {"target": "127.0.0.1", "protocol": "smb", "shares": True}),
    ("call_phase_sqlmap", "sqlmap", {"url": "http://127.0.0.1/login?id=1", "batch": True}),
    ("call_phase_hydra", "hydra", {"target": "127.0.0.1", "protocol": "ssh", "username": "admin", "password_file": "qa-passwords.txt"}),
    ("call_phase_metasploit", "metasploit", {"module": "exploit/multi/http/apache_path_traversal", "target": "127.0.0.1"}),
    ("call_phase_linpeas", "linpeas", {"target": "127.0.0.1"}),
]


class MockEngineHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"status": "ok", "model": "mock-autonomous-phase"})
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
            events = [{"choices": [{"delta": {"content": "Running authorized local phase checks."}}]}]
            for index, (call_id, name, arguments) in enumerate(TOOL_CALLS):
                events.append({
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": index,
                                "id": call_id,
                                "type": "function",
                                "function": {"name": name, "arguments": ""},
                            }]
                        }
                    }]
                })
                events.append({
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": index,
                                "function": {"arguments": json.dumps(arguments, sort_keys=True)},
                            }]
                        }
                    }]
                })
            events.append({
                "usage": {
                    "prompt_tokens": 240,
                    "completion_tokens": 40,
                    "prompt_tokens_details": {"cached_tokens": 16},
                },
                "choices": [{"delta": {}}],
            })
        else:
            events = [
                {"choices": [{"delta": {"content": "AUTONOMOUS_PHASE_FINAL: recon network web creds exploit post evidence captured."}}]},
                {
                    "usage": {
                        "prompt_tokens": 360,
                        "completion_tokens": 12,
                        "prompt_tokens_details": {"cached_tokens": 96},
                    },
                    "choices": [{"delta": {}}],
                },
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


def build_app_bundle() -> None:
    result = subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError("build_and_run --build-only failed")
    if not APP_BINARY.exists():
        raise RuntimeError(f"app binary missing after build: {APP_BINARY}")


def wait_until(predicate, label: str, timeout: float = 45.0):
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


def install_fake_tools(home: Path) -> Path:
    tools_dir = home / ".exploitbot" / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "nmap": "443/tcp open https Apache httpd 2.4.49\n",
        "netexec": "SMB 127.0.0.1 445 QA-SMB [*] Windows Server 2019 signing:false\n",
        "sqlmap": "GET parameter 'id' is vulnerable. injectable boolean-based blind SQL injection\n",
        "hydra": "[22][ssh] host: 127.0.0.1   login: admin   password: Password123!\n",
        "metasploit": "exploit/multi/http/apache_path_traversal\nMeterpreter session 7 opened (127.0.0.1:4444 -> 127.0.0.1:49158)\n",
        "msfconsole": "exploit/multi/http/apache_path_traversal\nMeterpreter session 7 opened (127.0.0.1:4444 -> 127.0.0.1:49158)\n",
        "linpeas.sh": "Hostname: qa-linux-01\nUser: www-data\n",
    }
    for name, output in outputs.items():
        script = tools_dir / name
        script.write_text(f"#!/usr/bin/python3\nimport sys\nsys.stdout.write({output!r})\n", encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return tools_dir


def run() -> None:
    mock = ThreadingHTTPServer(("127.0.0.1", 18996), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-phase-exec-home-")
    try:
        home = Path(temp_home.name)
        tools_dir = install_fake_tools(home)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        env["PATH"] = f"{tools_dir}:{env.get('PATH', '/usr/bin:/bin')}"
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        build_app_bundle()
        app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
        wait_for_app()

        request("POST", "/engine/mock", MOCK_ENGINE)
        request("POST", "/mode", "autopilot")
        request("POST", "/send", "Run authorized safe lab phase checks against loopback across recon, network, web, creds, exploit, and post.")

        try:
            messages = wait_until(
                lambda: (
                    current if "AUTONOMOUS_PHASE_FINAL" in json.dumps(current, sort_keys=True) else None
                ) if (current := request("GET", "/messages")) else None,
                "autonomous phase final answer",
            )
        except AssertionError as exc:
            debug_messages = request("GET", "/messages")
            debug_state = request("GET", "/state")
            raise AssertionError(
                f"{exc}; messages={debug_messages}; state={debug_state}"
            ) from exc
        text = json.dumps(messages, sort_keys=True)
        for tool in ("nmap", "netexec", "sqlmap", "hydra", "metasploit", "linpeas"):
            if tool not in text:
                raise AssertionError(f"chat transcript missing tool {tool}: {messages}")
        for marker in ("Tool request: nmap", "Tool request: netexec", "Tool request: sqlmap", "Tool request: hydra", "Tool request: metasploit", "Tool request: linpeas"):
            if marker not in text:
                raise AssertionError(f"verbose tool request missing {marker}: {messages}")

        state = request("GET", "/state")
        tabs = state.get("tabActivities") or {}
        expected_tabs = {
            "recon": "nmap",
            "network": "netexec",
            "web": "sqlmap",
            "creds": "hydra",
            "exploit": "metasploit",
            "post": "linpeas",
        }
        for tab, tool in expected_tabs.items():
            activity = tabs.get(tab) or {}
            if activity.get("lastTool") != tool or activity.get("status") != "done":
                raise AssertionError(f"{tab} activity missing {tool}: {state}")

        results = request("GET", "/results")
        if not any(port.get("port") == 443 and port.get("service") == "https" for port in results.get("ports", [])):
            raise AssertionError(f"recon nmap result missing from /results: {results}")
        parser_coverage = request("GET", "/qa/result-parser-coverage")
        if not any("127.0.0.1 QA-SMB ok" in host for host in parser_coverage.get("networkHosts", [])):
            raise AssertionError(f"network netexec result missing from parser coverage: {parser_coverage}")
        result_text = json.dumps(results, sort_keys=True)
        for marker in ("SQL Injection", "Valid Credentials Found", "Session:", "linpeas-host"):
            if marker not in result_text:
                raise AssertionError(f"parsed result missing {marker}: {results}")

        terminal = state.get("terminal") or {}
        transcript = json.dumps(terminal.get("commandTranscripts") or [], sort_keys=True)
        for tool in ("nmap", "netexec", "sqlmap", "hydra", "metasploit", "linpeas"):
            if tool not in transcript:
                raise AssertionError(f"terminal command transcript missing {tool}: {terminal}")

        with MockState.lock:
            if len(MockState.requests) < 2:
                raise AssertionError(f"model did not continue after tool calls: {MockState.requests}")

        print("autonomous-phase-execution proof passed")
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
        print(f"autonomous-phase-execution proof failed: {exc}", flush=True)
        raise SystemExit(1)
