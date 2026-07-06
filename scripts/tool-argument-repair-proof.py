#!/usr/bin/env python3
from __future__ import annotations

import json
import os
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
from typing import Any

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-tool-argument-repair.json"
FINAL_MARKER = "TOOL_ARGUMENT_REPAIR_FINAL"


class MockState:
    lock = threading.Lock()
    requests: list[dict[str, Any]] = []
    emitted_empty_httpx_arguments = False
    target = ""


class MockEngineHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"status": "ok", "model": "mock-empty-httpx-arguments"})
            return
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
            MockState.emitted_empty_httpx_arguments = True
            events = [
                {"choices": [{"delta": {"content": "I will probe the scoped local web service with httpx."}}]},
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_empty_httpx",
                                        "type": "function",
                                        "function": {"name": "httpx", "arguments": "{}"},
                                    }
                                ]
                            }
                        }
                    ]
                },
            ]
        else:
            events = [{"choices": [{"delta": {"content": FINAL_MARKER}}]}]
        events.append({"usage": {"prompt_tokens": 100 + turn, "completion_tokens": 20}, "choices": [{"delta": {}}]})
        for event in events:
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
            self.wfile.flush()
            time.sleep(0.02)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def _json(self, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_fake_httpx(tools_dir: Path, target: str) -> tuple[Path, Path | None]:
    tools_dir.mkdir(parents=True, exist_ok=True)
    httpx_path = tools_dir / "httpx"
    backup_path: Path | None = None
    if httpx_path.exists():
        backup_path = tools_dir / f"httpx.exploitbot-backup-{int(time.time() * 1000)}"
        httpx_path.rename(backup_path)
    write_executable(
        httpx_path,
        f"""#!/usr/bin/python3
import json
import sys
raw = sys.stdin.read().strip()
print(json.dumps({{"input": raw, "url": raw, "expected": "{target}", "title": "ExploitBot Argument Repair Lab", "status_code": 200}}))
""",
    )
    return httpx_path, backup_path


def restore_httpx(httpx_path: Path | None, backup_path: Path | None) -> None:
    if httpx_path is not None and httpx_path.exists():
        httpx_path.unlink()
    if backup_path is not None and backup_path.exists():
        backup_path.rename(httpx_path)


def request(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 8.0) -> Any:
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def wait_until(predicate, label: str, timeout: float = 45.0) -> Any:
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


def build_app_bundle() -> None:
    result = subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError("build_and_run --build-only failed")
    if not APP_BINARY.exists():
        raise RuntimeError(f"app binary missing after build: {APP_BINARY}")


def run() -> None:
    started = timestamp()
    mock_port = free_port()
    target = f"http://127.0.0.1:{free_port()}"
    MockState.target = target
    mock = ThreadingHTTPServer(("127.0.0.1", mock_port), MockEngineHandler)
    thread = threading.Thread(target=mock.serve_forever, daemon=True)
    thread.start()
    app: subprocess.Popen[str] | None = None
    httpx_path: Path | None = None
    httpx_backup_path: Path | None = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-argument-repair-home-")
    try:
        with app_proof_lock("tool-argument-repair-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            home = Path(temp_home.name)
            install_fake_httpx(home / ".exploitbot" / "tools", target)
            httpx_path, httpx_backup_path = install_fake_httpx(Path.home() / ".exploitbot" / "tools", target)
            env = os.environ.copy()
            env["EXPLOITBOT_TESTING"] = "1"
            env["HOME"] = str(home)
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_until(lambda: request("GET", "/state", timeout=1.0), "app test server")

            request("POST", "/engine/mock", f"http://127.0.0.1:{mock_port}")
            request("POST", "/mode", "autopilot")
            request("POST", "/tab", "web")
            request(
                "POST",
                "/qa/apply-app-settings",
                {
                    "maxIterations": 2,
                    "toolSchemaMaxTools": 8,
                    "includeUnavailableToolSchemas": True,
                    "toolSchemaExcludedTools": ["run_shell"],
                    "forceFinalAnswerAfterToolResults": True,
                    "followAgent": False,
                },
            )
            prompt = f"Authorized local fixture only. Target scope is only {target}. Probe it with the available web tool and report the result."
            request("POST", "/send", prompt)
            wait_until(lambda: not request("GET", "/state").get("isWorking"), "chat turn completion", timeout=60.0)
            messages = request("GET", "/messages")
            state = request("GET", "/state")

        messages_text = json.dumps(messages, sort_keys=True)
        state_text = json.dumps(state, sort_keys=True)
        checks = {
            "modelEmittedEmptyHttpxArguments": "PASS" if MockState.emitted_empty_httpx_arguments else "FAIL",
            "repairNoticeVisible": "PASS" if "Tool arguments repaired from scoped local prompt target" in messages_text else "FAIL",
            "httpxCommandUsesTarget": "PASS" if target in messages_text else "FAIL",
            "httpxOutputReceivedTarget": "PASS" if f'\\"input\\": \\"{target}\\"' in messages_text or f'"input": "{target}"' in messages_text else "FAIL",
            "noEmptyHttpxCommand": "PASS" if "echo '' | tr" not in messages_text else "FAIL",
            "mockEngineOnly": "PASS" if state.get("model") == "mock-empty-httpx-arguments" or state.get("healthStatus") == "mock engine connected" else "FAIL",
        }
        ok = all(value == "PASS" for value in checks.values())
        report = {
            "ok": ok,
            "proofType": "tool-argument-repair-live-app",
            "generatedAt": timestamp(),
            "startedAt": started,
            "finishedAt": timestamp(),
            "target": target,
            "status": "PASS" if ok else "FAIL",
            "checks": checks,
            "messages": messages,
            "chat": state.get("chat") or {},
            "requestContext": state.get("requestContext") or {},
            "modelRequests": MockState.requests,
        }
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not ok:
            raise AssertionError(f"tool argument repair proof failed: {checks}")
        print(f"tool argument repair proof passed and wrote {ARTIFACT}")
    finally:
        mock.shutdown()
        temp_home.cleanup()
        restore_httpx(httpx_path, httpx_backup_path)
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app and app.poll() is None:
            app.terminate()


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"tool argument repair proof failed: {exc}", flush=True)
        raise SystemExit(1)
