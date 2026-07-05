#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import re
import shutil
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
MOCK_ENGINE_PORT = 18997
MOCK_ENGINE = f"http://127.0.0.1:{MOCK_ENGINE_PORT}"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-real-installed-tools-loopback.json"
CORE_PENTEST_TOOLS = ["nmap", "httpx", "nuclei", "sqlmap", "hydra", "msfconsole", "netexec", "linpeas.sh"]
REQUIRED_REAL_TOOLS = ["curl", "nc", "python3", "nmap"]
OPTIONAL_LOOPBACK_TOOLS = ["httpx", "nuclei", "hydra", "netexec", "linpeas.sh"]


class LabHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/protected":
            expected = "Basic " + base64.b64encode(b"admin:letmein").decode("ascii")
            if self.headers.get("Authorization") == expected:
                body = b"EXPLOITBOT_HYDRA_LAB_OK\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            body = b"auth required\n"
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="ExploitBot"')
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/vuln":
            body = b"EXPLOITBOT_NUCLEI_LAB_OK\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("X-ExploitBot-Lab", "loopback-real-tool")
            self.send_header("X-ExploitBot-Vuln", "nuclei-proof")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/httpx":
            body = b"<html><title>ExploitBot HTTPX Lab</title>EXPLOITBOT_HTTPX_LAB_OK</html>\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("X-ExploitBot-Lab", "httpx-proof")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        body = (
            "EXPLOITBOT_LOOPBACK_LAB_OK\n"
            "service=lab-http\n"
            "cve=CVE-2026-45659\n"
            f"path={self.path}\n"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("X-ExploitBot-Lab", "loopback-real-tool")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class MockState:
    lock = threading.Lock()
    requests: list[dict[str, Any]] = []
    lab_port = 0
    nuclei_template = ""
    hydra_password_file = ""


class MockEngineHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"status": "ok", "model": "mock-real-installed-tools"})
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
            lab_port = MockState.lab_port

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        if turn == 1:
            nmap_args = {"target": "127.0.0.1", "ports": str(lab_port), "service_detection": True}
            httpx_args = {
                "targets": f"http://127.0.0.1:{lab_port}/httpx",
                "status_code": True,
                "title": True,
                "tech_detect": True,
            }
            nuclei_args = {
                "target": f"http://127.0.0.1:{lab_port}",
                "templates": MockState.nuclei_template,
            }
            hydra_args = {
                "target": "127.0.0.1",
                "protocol": "http-get",
                "port": lab_port,
                "path": "/protected",
                "username": "admin",
                "password_file": MockState.hydra_password_file,
            }
            netexec_args = {
                "target": "127.0.0.1",
                "protocol": "smb",
                "shares": True,
                "timeout": 2,
                "smb_timeout": 2,
            }
            linpeas_args = {"flags": "-q -N -o system_information"}
            curl_command = f"curl -sS -i 'http://127.0.0.1:{lab_port}/proof?tool=curl'"
            nc_command = (
                "printf 'GET /proof?tool=nc HTTP/1.1\\r\\n"
                f"Host: 127.0.0.1:{lab_port}\\r\\nConnection: close\\r\\n\\r\\n' "
                f"| nc 127.0.0.1 {lab_port}"
            )
            events: list[dict[str, Any]] = [
                {"choices": [{"delta": {"content": "Executing real installed loopback tools through run_shell."}}]},
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 0,
                                "id": "call_real_nmap",
                                "type": "function",
                                "function": {"name": "nmap", "arguments": ""},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 0,
                                "function": {"arguments": json.dumps(nmap_args)},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 1,
                                "id": "call_real_httpx",
                                "type": "function",
                                "function": {"name": "httpx", "arguments": ""},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 1,
                                "function": {"arguments": json.dumps(httpx_args)},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 2,
                                "id": "call_real_nuclei",
                                "type": "function",
                                "function": {"name": "nuclei", "arguments": ""},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 2,
                                "function": {"arguments": json.dumps(nuclei_args)},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 3,
                                "id": "call_real_hydra",
                                "type": "function",
                                "function": {"name": "hydra", "arguments": ""},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 3,
                                "function": {"arguments": json.dumps(hydra_args)},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 4,
                                "id": "call_real_netexec",
                                "type": "function",
                                "function": {"name": "netexec", "arguments": ""},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 4,
                                "function": {"arguments": json.dumps(netexec_args)},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 5,
                                "id": "call_real_linpeas",
                                "type": "function",
                                "function": {"name": "linpeas", "arguments": ""},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 5,
                                "function": {"arguments": json.dumps(linpeas_args)},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 6,
                                "id": "call_real_curl",
                                "type": "function",
                                "function": {"name": "run_shell", "arguments": ""},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 6,
                                "function": {"arguments": json.dumps({"command": curl_command})},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 7,
                                "id": "call_real_nc",
                                "type": "function",
                                "function": {"name": "run_shell", "arguments": ""},
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 7,
                                "function": {"arguments": json.dumps({"command": nc_command})},
                            }]
                        }
                    }]
                },
                {
                    "usage": {
                        "prompt_tokens": 260,
                        "completion_tokens": 80,
                        "prompt_tokens_details": {"cached_tokens": 32},
                    },
                    "choices": [{"delta": {}}],
                },
            ]
        else:
            events = [
                {"choices": [{"delta": {"content": "REAL_INSTALLED_TOOLS_FINAL: nmap, httpx, nuclei, hydra, netexec, linpeas, curl, and nc loopback outputs were captured in chat, terminal transcripts, activity feed, and raw results."}}]},
                {
                    "usage": {
                        "prompt_tokens": 420,
                        "completion_tokens": 24,
                        "prompt_tokens_details": {"cached_tokens": 128},
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

    def _json(self, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 8.0):
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


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


def build_app_bundle() -> None:
    result = subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError("build_and_run --build-only failed")
    if not APP_BINARY.exists():
        raise RuntimeError(f"app binary missing after build: {APP_BINARY}")


def command_path(name: str) -> str | None:
    for candidate in (
        Path("/Users/eric/.exploitbot/tools") / name,
        Path("/Users/eric/.local/bin") / name,
        Path("/opt/homebrew/bin") / name,
        Path("/usr/local/bin") / name,
        Path("/usr/bin") / name,
        Path("/bin") / name,
    ):
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    found = subprocess.run(["/bin/sh", "-lc", f"command -v {name}"], text=True, capture_output=True)
    path = found.stdout.strip()
    return path or None


def command_version(path: str, *args: str) -> str:
    result = subprocess.run([path, *args], text=True, capture_output=True)
    output = result.stdout + result.stderr
    match = re.search(r"\d+\.\d+(?:\.\d+)?", output)
    return match.group(0) if match else ""


def tool_inventory() -> dict[str, Any]:
    installed = {tool: command_path(tool) for tool in REQUIRED_REAL_TOOLS + CORE_PENTEST_TOOLS}
    return {
        "installed": {tool: path for tool, path in installed.items() if path},
        "missingPentestTools": [tool for tool in CORE_PENTEST_TOOLS if not installed.get(tool)],
        "requiredRealToolsPresent": all(installed.get(tool) for tool in REQUIRED_REAL_TOOLS),
        "optionalLoopbackToolsPresent": {
            tool: bool(installed.get(tool)) for tool in OPTIONAL_LOOPBACK_TOOLS
        },
    }


def write_lab_assets(home: Path) -> tuple[Path, Path]:
    template_dir = home / ".exploitbot" / "nuclei-templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    template = template_dir / "exploitbot-loopback.yaml"
    template.write_text(
        """id: exploitbot-loopback-header

info:
  name: EXPLOITBOT_NUCLEI_LAB_OK
  author: exploitbot
  severity: high

http:
  - method: GET
    path:
      - "{{BaseURL}}/vuln"
    matchers:
      - type: word
        part: body
        words:
          - "EXPLOITBOT_NUCLEI_LAB_OK"
""",
        encoding="utf-8",
    )
    password_file = home / ".exploitbot" / "hydra-passwords.txt"
    password_file.write_text("wrongpass\nletmein\n", encoding="utf-8")
    user_httpx = Path("/Users/eric/.exploitbot/tools/httpx")
    if user_httpx.exists():
        tool_dir = home / ".exploitbot" / "tools"
        tool_dir.mkdir(parents=True, exist_ok=True)
        staged_httpx = tool_dir / "httpx"
        shutil.copy2(user_httpx, staged_httpx)
        staged_httpx.chmod(0o755)
    user_linpeas = Path("/Users/eric/.exploitbot/tools/linpeas.sh")
    if user_linpeas.exists():
        tool_dir = home / ".exploitbot" / "tools"
        tool_dir.mkdir(parents=True, exist_ok=True)
        staged_linpeas = tool_dir / "linpeas.sh"
        shutil.copy2(user_linpeas, staged_linpeas)
        staged_linpeas.chmod(0o755)
    user_netexec = Path("/Users/eric/.local/bin/netexec")
    if user_netexec.exists():
        local_bin = home / ".local" / "bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        (local_bin / "netexec").symlink_to(user_netexec)
        nxc = Path("/Users/eric/.local/bin/nxc")
        if nxc.exists():
            (local_bin / "nxc").symlink_to(nxc)
    return template, password_file


def run() -> None:
    output = Path(os.environ.get("EXPLOITBOT_REAL_INSTALLED_TOOLS_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    lab_port = free_port()
    MockState.lab_port = lab_port
    lab = ThreadingHTTPServer(("127.0.0.1", lab_port), LabHandler)
    lab_thread = threading.Thread(target=lab.serve_forever, daemon=True)
    lab_thread.start()
    mock = ThreadingHTTPServer(("127.0.0.1", MOCK_ENGINE_PORT), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-real-installed-tools-home-")
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "real-installed-tools-loopback",
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "labUrl": f"http://127.0.0.1:{lab_port}/proof",
        "toolInventory": tool_inventory(),
    }
    error: Exception | None = None
    try:
        if not report["toolInventory"]["requiredRealToolsPresent"]:
            raise AssertionError(f"required loopback tools missing: {report['toolInventory']}")
        missing_optional_loopback = [
            tool for tool, present in report["toolInventory"]["optionalLoopbackToolsPresent"].items()
            if not present
        ]
        if missing_optional_loopback:
            raise AssertionError(f"optional loopback proof tools missing: {missing_optional_loopback}")

        home = Path(temp_home.name)
        nuclei_template, hydra_password_file = write_lab_assets(home)
        MockState.nuclei_template = str(nuclei_template)
        MockState.hydra_password_file = str(hydra_password_file)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        build_app_bundle()
        app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
        wait_until(lambda: request("GET", "/state", timeout=1.0), "app test server")

        request("POST", "/engine/mock", MOCK_ENGINE)
        request("POST", "/mode", "autopilot")
        request("POST", "/reasoning", "off")
        request(
            "POST",
            "/qa/apply-app-settings",
            {
                "maxIterations": 4,
                "forceFinalAnswerAfterToolResults": False,
                "toolSchemaMaxTools": 16,
                "includeUnavailableToolSchemas": True,
                "chat": {"enableReasoning": False},
            },
        )
        prompt = (
            "Authorized safe lab proof. Use nmap, httpx, nuclei, hydra, netexec, linpeas, and run_shell only against loopback 127.0.0.1 or the local host. "
            "Execute the real installed nmap, httpx, nuclei, hydra, netexec, linpeas, curl, and nc checks requested by the engine, then produce the final marker."
        )
        request("POST", "/send", prompt)
        messages = wait_until(
            lambda: (
                current if "REAL_INSTALLED_TOOLS_FINAL" in json.dumps(current, sort_keys=True) else None
            ) if (current := request("GET", "/messages")) else None,
            "real installed tools final answer",
        )
        state = request("GET", "/state")
        results = request("GET", "/results")

        messages_text = json.dumps(messages, sort_keys=True)
        state_text = json.dumps(state, sort_keys=True)
        results_text = json.dumps(results, sort_keys=True)
        for marker in (
            "Tool request: nmap",
            "Tool request: httpx",
            "Tool request: nuclei",
            "Tool request: hydra",
            "Tool request: netexec",
            "Tool request: linpeas",
            str(lab_port),
            "nmap -p",
            "ExploitBot HTTPX Lab",
            "status_code",
            "exploitbot-loopback-header",
            "http-get",
            "admin",
            "SMB",
            "MacPEAS-ng",
            "Tool request: run_shell",
            "curl -sS -i 'http://127.0.0.1",
            "| nc 127.0.0.1",
            f"{lab_port}/tcp",
            "open",
            "EXPLOITBOT_LOOPBACK_LAB_OK",
            "X-ExploitBot-Lab",
            "REAL_INSTALLED_TOOLS_FINAL",
        ):
            if marker not in messages_text:
                raise AssertionError(f"chat transcript missing {marker!r}: {messages}")

        terminal = state.get("terminal") or {}
        transcript = json.dumps(terminal.get("commandTranscripts") or [], sort_keys=True)
        for marker in (
            "nmap",
            f"{lab_port}/tcp",
            "httpx",
            "ExploitBot HTTPX Lab",
            "nuclei",
            "exploitbot-loopback-header",
            "hydra",
            "http-get",
            "letmein",
            "netexec",
            "SMB",
            "linpeas",
            "MacPEAS-ng",
            "run_shell",
            "curl -sS -i",
            "| nc 127.0.0.1",
            "EXPLOITBOT_LOOPBACK_LAB_OK",
        ):
            if marker not in transcript:
                raise AssertionError(f"terminal commandTranscripts missing {marker!r}: {terminal}")

        feed_text = json.dumps(state.get("feedRecent") or [], sort_keys=True)
        for marker in ("Running run_shell", "run_shell:"):
            if marker not in feed_text:
                raise AssertionError(f"activity feed missing {marker!r}: {state.get('feedRecent')}")

        for marker in (
            f"{lab_port}/tcp",
            "open",
            "EXPLOITBOT_LOOPBACK_LAB_OK",
            "CVE-2026-45659",
            "lab-http",
            "ExploitBot HTTPX Lab",
            "exploitbot-loopback-header",
            "hydra",
            "http-get",
            "letmein",
            "SMB",
            "MacPEAS-ng",
        ):
            if marker not in results_text:
                raise AssertionError(f"raw results missing {marker!r}: {results}")

        with MockState.lock:
            request_count = len(MockState.requests)
            requests = list(MockState.requests)
        if request_count < 2:
            raise AssertionError(f"model did not receive tool results and continue: {requests}")

        report.update(
            {
                "ok": True,
                "messages": messages,
                "state": state,
                "results": results,
                "mockRequestCount": request_count,
                "nmapPath": command_path("nmap"),
                "httpxPath": str(home / ".exploitbot" / "tools" / "httpx"),
                "nucleiPath": command_path("nuclei"),
                "hydraPath": command_path("hydra"),
                "netexecPath": str(home / ".local" / "bin" / "netexec"),
                "linpeasPath": str(home / ".exploitbot" / "tools" / "linpeas.sh"),
                "nmapVersion": subprocess.run(["nmap", "--version"], text=True, capture_output=True).stdout.splitlines()[:3],
                "httpxVersion": command_version(str(home / ".exploitbot" / "tools" / "httpx"), "-version"),
                "nucleiVersion": subprocess.run(["nuclei", "-version"], text=True, capture_output=True).stdout.splitlines()[:3],
                "hydraVersion": subprocess.run(["hydra", "-h"], text=True, capture_output=True).stdout.splitlines()[:3],
                "netexecVersion": command_version(str(home / ".local" / "bin" / "netexec"), "--version"),
                "chatContainsRealToolOutput": "EXPLOITBOT_LOOPBACK_LAB_OK" in messages_text,
                "chatContainsNmapOutput": f"{lab_port}/tcp" in messages_text,
                "chatContainsHttpxOutput": "ExploitBot HTTPX Lab" in messages_text,
                "chatContainsNucleiOutput": "exploitbot-loopback-header" in messages_text,
                "chatContainsHydraOutput": "http-get" in messages_text,
                "chatContainsNetexecOutput": "SMB" in messages_text,
                "chatContainsLinpeasOutput": "MacPEAS-ng" in messages_text,
                "terminalContainsRealToolOutput": "EXPLOITBOT_LOOPBACK_LAB_OK" in transcript,
                "terminalContainsNmapOutput": f"{lab_port}/tcp" in transcript,
                "terminalContainsHttpxOutput": "ExploitBot HTTPX Lab" in transcript,
                "terminalContainsNucleiOutput": "exploitbot-loopback-header" in transcript,
                "terminalContainsHydraOutput": "letmein" in transcript,
                "terminalContainsNetexecOutput": "SMB" in transcript,
                "terminalContainsLinpeasOutput": "MacPEAS-ng" in transcript,
                "resultsContainRealToolOutput": "EXPLOITBOT_LOOPBACK_LAB_OK" in results_text,
                "resultsContainNmapOutput": f"{lab_port}/tcp" in results_text,
                "resultsContainHttpxOutput": "ExploitBot HTTPX Lab" in results_text,
                "resultsContainNucleiOutput": "exploitbot-loopback-header" in results_text,
                "resultsContainHydraOutput": "letmein" in results_text,
                "resultsContainNetexecOutput": "SMB" in results_text,
                "resultsContainLinpeasOutput": "MacPEAS-ng" in results_text,
                "status": {
                    "realInstalledNmapLoopback": "PASS",
                    "realInstalledHttpxLoopback": "PASS",
                    "realInstalledNucleiLoopback": "PASS",
                    "realInstalledHydraLoopback": "PASS",
                    "realInstalledNetexecLoopback": "PASS",
                    "realInstalledLinpeasLocal": "PASS",
                    "realInstalledCurlNcLoopback": "PASS",
                    "fullPentestToolchainInstalled": "PASS" if not report["toolInventory"]["missingPentestTools"] else "PARTIAL",
                    "missingPentestTools": report["toolInventory"]["missingPentestTools"],
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
        mock.shutdown()
        lab.shutdown()
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
    print("real-installed-tools-loopback proof passed")


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"real-installed-tools-loopback proof failed: {exc}", flush=True)
        raise SystemExit(1)
