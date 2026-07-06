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
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
MOCK_ENGINE = "http://127.0.0.1:19018"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-webserver-auth-sqli-scenario.json"
STAGES = ["surface", "probe", "prove", "exploit_or_validate", "evidence", "report"]
EXPECTED_TOOLS = ["run_shell", "httpx", "nuclei", "sqlmap", "search_cve"]
FINAL_MARKER = "WEBAPP_SQLI_FINAL"


class LabState:
    port = 0


class WebLabHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/routes":
            self._text("GET /\nGET /login\nGET /search?q=1\n")
            return
        if parsed.path == "/login":
            self._text("<html><title>ExploitBot SQLi Lab Login</title><form>login</form></html>\n", "text/html")
            return
        if parsed.path == "/search":
            query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
            if "'" in query or "1=1" in query.lower():
                self._text("EXPLOITBOT_SQLI_PROOF_USER=alice\nparameter=q\n")
            else:
                self._text("no rows\n")
            return
        self._text("<html><title>ExploitBot SQLi Lab</title>EXPLOITBOT_WEBAPP_LAB_OK</html>\n", "text/html")

    def _text(self, body: str, content_type: str = "text/plain") -> None:
        raw = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class MockState:
    lock = threading.Lock()
    requests: list[dict[str, Any]] = []
    lab_url = ""


class MockEngineHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"status": "ok", "model": "mock-webserver-auth-sqli"})
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
            lab_url = MockState.lab_url

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        if turn == 1:
            route_cmd = f"curl -sS {lab_url}/routes && curl -sS '{lab_url}/search?q=1%27%20OR%201%3D1--'"
            tool_calls = [
                ("call_web_routes", "run_shell", {"command": route_cmd}),
                ("call_web_httpx", "httpx", {"targets": lab_url, "status_code": True, "title": True, "tech_detect": True}),
                ("call_web_nuclei", "nuclei", {"target": lab_url, "templates": "webserver-auth-sqli-local"}),
                ("call_web_sqlmap", "sqlmap", {"url": f"{lab_url}/search?q=1", "level": 2, "risk": 1, "dbs": True}),
                ("call_web_cve", "search_cve", {"query": "CVE-2021-41773 SQL injection", "product": "apache", "max_results": 5}),
            ]
            events: list[dict[str, Any]] = [
                {"choices": [{"delta": {"content": "Starting local web app auth and SQL injection workflow."}}]},
            ]
            for index, (call_id, name, arguments) in enumerate(tool_calls):
                events.append(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": index,
                                            "id": call_id,
                                            "type": "function",
                                            "function": {"name": name, "arguments": ""},
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                )
                events.append(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": index,
                                            "function": {"arguments": json.dumps(arguments, sort_keys=True)},
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                )
        else:
            events = [
                {
                    "choices": [
                        {
                            "delta": {
                                "content": (
                                    f"{FINAL_MARKER}: discovered the loopback web app, probed httpx/nuclei, "
                                    "validated SQL injection on GET parameter q with sqlmap-style evidence, "
                                    "and queued report evidence from the local fixture only."
                                )
                            }
                        }
                    ]
                }
            ]

        events.append(
            {
                "usage": {
                    "prompt_tokens": 300 + turn,
                    "completion_tokens": 72,
                    "prompt_tokens_details": {"cached_tokens": 24 * turn},
                },
                "choices": [{"delta": {}}],
            }
        )
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


def passfail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 8.0) -> Any:
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def wait_until(predicate, label: str, timeout: float = 90.0) -> Any:
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


def write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_fake_web_tools_at(tools_dir: Path, lab_url: str) -> Path:
    tools_dir.mkdir(parents=True, exist_ok=True)
    write_executable(
        tools_dir / "httpx",
        f"""#!/usr/bin/python3
import json
print(json.dumps({{"url": "{lab_url}", "input": "{lab_url}", "status_code": 200, "title": "ExploitBot SQLi Lab", "webserver": "ExploitBotLab/1.0", "tech": ["python", "sqlite"]}}))
""",
    )
    write_executable(
        tools_dir / "nuclei",
        f"""#!/usr/bin/python3
import json
print(json.dumps({{
  "template-id": "webserver-auth-sqli-local",
  "matched-at": "{lab_url}/search?q=1",
  "host": "{lab_url}",
  "info": {{
    "name": "Local SQL injection proof",
    "severity": "high",
    "description": "Loopback SQL injection proof for q parameter.",
    "classification": {{"cve-id": "CVE-2021-41773"}},
    "tags": ["sqli", "local-fixture"]
  }}
}}))
""",
    )
    write_executable(
        tools_dir / "sqlmap",
        """#!/usr/bin/python3
print("[INFO] testing GET parameter 'q'")
print("Parameter: q (GET)")
print("    Type: boolean-based blind")
print("    Title: OR boolean-based blind - WHERE or HAVING clause")
print("EXPLOITBOT_SQLI_PROOF_USER=alice")
print("available databases [1]:")
print("[*] exploitbot_lab")
""",
    )
    return tools_dir


def tool_sequence(messages: list[dict[str, Any]]) -> list[str]:
    sequence = []
    for message in messages:
        tool = str(message.get("tool") or "").strip()
        content = str(message.get("content") or "")
        if not tool and content.lower().startswith("tool request: "):
            tool = content.splitlines()[0].split(":", 1)[-1].strip()
        if message.get("role") == "toolCall" and tool:
            sequence.append(tool)
    return sequence


def ordered_subsequence(actual: list[str], expected: list[str]) -> bool:
    cursor = 0
    for item in expected:
        while cursor < len(actual) and actual[cursor] != item:
            cursor += 1
        if cursor >= len(actual):
            return False
        cursor += 1
    return True


def has_assistant_marker(messages: list[dict[str, Any]], marker: str) -> bool:
    return any(
        message.get("role") == "assistant" and marker in str(message.get("content") or "")
        for message in messages
    )


def model_schema_names(model_requests: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for request_payload in model_requests:
        for tool in request_payload.get("tools") or []:
            name = ((tool.get("function") or {}).get("name") or "").strip()
            if name:
                names.append(name)
    return names


def build_report(
    *,
    started_at: str,
    finished_at: str,
    lab_url: str,
    messages: list[dict[str, Any]],
    state: dict[str, Any],
    results: dict[str, Any],
    report_state: dict[str, Any],
    model_requests: list[dict[str, Any]],
) -> dict[str, Any]:
    text = json.dumps(messages, sort_keys=True)
    results_text = json.dumps(results, sort_keys=True)
    state_text = json.dumps(state, sort_keys=True)
    report_text = json.dumps(report_state, sort_keys=True)
    terminal_text = json.dumps(((state.get("terminal") or {}).get("commandTranscripts") or []), sort_keys=True)
    sequence = tool_sequence(messages)
    schema_names = model_schema_names(model_requests)
    raw_tools = [row.get("tool") for row in results.get("rawResults") or [] if isinstance(row, dict)]
    vulns = results.get("vulns") or []
    vuln_sources = {row.get("source") for row in vulns if isinstance(row, dict)}
    checks = {
        "modelReceivedWebToolSchemas": passfail(all(tool in schema_names for tool in EXPECTED_TOOLS)),
        "orderedToolSequence": passfail(ordered_subsequence(sequence, EXPECTED_TOOLS)),
        "verboseToolTranscript": passfail(all(f"Tool request: {tool}" in text for tool in EXPECTED_TOOLS)),
        "modelContinuedAfterTools": passfail(len(model_requests) >= 2 and FINAL_MARKER in text),
        "webSurfaceEvidence": passfail("/login" in text and "/search?q=1" in text and "ExploitBot SQLi Lab" in results_text),
        "httpProbeEvidence": passfail("httpx" in raw_tools and "ExploitBot SQLi Lab" in results_text),
        "nucleiEvidence": passfail("nuclei" in vuln_sources and "webserver-auth-sqli-local" in results_text),
        "sqlInjectionProof": passfail("sqlmap" in raw_tools and "Parameter: q" in results_text and "EXPLOITBOT_SQLI_PROOF_USER=alice" in results_text),
        "cveContextEvidence": passfail("CVE-2021-41773" in text or "CVE-2021-41773" in results_text),
        "safeLocalBoundary": passfail(lab_url.startswith("http://127.0.0.1:") and "http://example" not in text),
        "rawResultEvidence": passfail(all(tool in results_text for tool in ["httpx", "nuclei", "sqlmap"])),
        "terminalTranscripts": passfail(all(tool in terminal_text for tool in ["httpx", "nuclei", "sqlmap"])),
        "reportGeneratedFromEvidence": passfail(
            "reportRenderActions" in report_text
            and "done" in report_text
            and "SQL injection in local search parameter" in report_text
            and "EXPLOITBOT_SQLI_PROOF_USER=alice" in report_text
        ),
    }
    ok = all(value == "PASS" for value in checks.values())
    return {
        "ok": ok,
        "proofType": "webserver-auth-sqli-scenario-live",
        "proofLevel": "live-app-mock-engine-real-tool-executor-fake-local-web-scanners",
        "status": "PASS" if ok else "FAIL",
        "scenarioId": "webserver_auth_sqli_report_chain",
        "generatedAt": finished_at,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "labUrl": lab_url,
        "stages": STAGES,
        "stageEvidence": {
            "surface": ["run_shell route inventory", "httpx local web probe"],
            "probe": ["nuclei local template", "sqlmap local query parameter test"],
            "prove": ["q parameter SQL injection proof marker", "nuclei structured finding"],
            "exploit_or_validate": ["bounded local validation only; no external targets"],
            "evidence": ["/messages tool cards", "/results rawResults/vulns", "/state terminal transcripts"],
            "report": ["/qa/finding-wizard-submit", "/qa/report-generate-action"],
        },
        "toolSequence": sequence,
        "expectedToolSequence": EXPECTED_TOOLS,
        "toolSchemaNames": sorted(set(schema_names)),
        "checks": checks,
        "messages": messages,
        "resultsSummary": {
            "webHostCount": len(results.get("webHosts") or []),
            "vulnCount": len(vulns),
            "vulnSources": sorted(source for source in vuln_sources if source),
            "rawResultCount": len(results.get("rawResults") or []),
            "rawTools": raw_tools,
        },
        "reportRenderActions": report_state.get("reportRenderActions") or {},
        "notes": [
            "Scenario uses a loopback webserver and deterministic local scanner shims on isolated PATH.",
            "The SQL injection validation is a local fixture proof marker, not an external target exploit.",
            "This proves app orchestration, verbose transcript, parser/raw result ingestion, and report route wiring.",
        ],
    }


def submit_report_from_results(lab_url: str, results: dict[str, Any]) -> dict[str, Any]:
    created = request(
        "POST",
        "/qa/finding-wizard-submit",
        {
            "title": "SQL injection in local search parameter",
            "vulnType": "sql_injection",
            "target": f"{lab_url}/search?q=1",
            "severity": "high",
            "cvss": 8.1,
            "description": "The local fixture search endpoint exposes SQL injection evidence in the q parameter.",
            "impact": "An attacker could alter query logic and extract application data.",
            "remediation": "Use parameterized queries and add regression coverage for q input handling.",
            "cveId": "CVE-2021-41773",
            "evidence": [
                "sqlmap reported Parameter: q (GET)",
                "EXPLOITBOT_SQLI_PROOF_USER=alice",
                "nuclei template webserver-auth-sqli-local",
            ],
        },
        timeout=15.0,
    )
    if created.get("ok") is not True:
        raise AssertionError(f"report finding create failed: {created}")
    generated = request("POST", "/qa/report-generate-action", {"template": "Full Report"}, timeout=15.0)
    if generated.get("ok") is not True:
        raise AssertionError(f"report generation failed: {generated}")
    return generated


def run() -> None:
    started_at = timestamp()
    lab_port = free_port()
    lab_url = f"http://127.0.0.1:{lab_port}"
    LabState.port = lab_port
    MockState.lab_url = lab_url
    lab = ThreadingHTTPServer(("127.0.0.1", lab_port), WebLabHandler)
    lab_thread = threading.Thread(target=lab.serve_forever, daemon=True)
    lab_thread.start()
    mock = ThreadingHTTPServer(("127.0.0.1", 19018), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-web-sqli-home-", ignore_cleanup_errors=True)
    report: dict[str, Any] = {"ok": False, "proofType": "webserver-auth-sqli-scenario-live", "startedAt": started_at}
    error: Exception | None = None
    try:
        home = Path(temp_home.name)
        tools_dir = install_fake_web_tools_at(home / ".exploitbot" / "tools", lab_url)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        env["PATH"] = f"{tools_dir}:{env.get('PATH', '/usr/bin:/bin')}"

        with app_proof_lock("webserver-auth-sqli-scenario-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            install_fake_web_tools_at(APP_BINARY.parents[1] / "Resources" / "tools", lab_url)
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_until(lambda: request("GET", "/state", timeout=1.0), "app test server")

            request("POST", "/engine/mock", MOCK_ENGINE)
            request("POST", "/mode", "autopilot")
            request("POST", "/reasoning", "off")
            request("POST", "/tab", "web")
            request("POST", "/qa/apply-app-settings", {"toolSchemaMaxTools": 64, "maxIterations": 6})
            request(
                "POST",
                "/send",
                (
                    "Authorized local webserver lab only. Use run_shell, httpx, nuclei, sqlmap, and search_cve "
                    f"against this loopback target only: {lab_url}. Surface routes, probe the web app, prove the "
                    f"q parameter SQL injection with local fixture evidence, then summarize with {FINAL_MARKER}."
                ),
            )

            messages = wait_until(
                lambda: (
                    current if has_assistant_marker(current, FINAL_MARKER) else None
                ) if (current := request("GET", "/messages")) else None,
                "webserver SQLi final answer",
            )
            state = request("GET", "/state")
            results = request("GET", "/results")
            submit_report_from_results(lab_url, results)
            report_state = request("GET", "/state")
            with MockState.lock:
                model_requests = list(MockState.requests)
            report = build_report(
                started_at=started_at,
                finished_at=timestamp(),
                lab_url=lab_url,
                messages=messages,
                state=state,
                results=results,
                report_state=report_state,
                model_requests=model_requests,
            )
            if not report["ok"]:
                raise AssertionError("webserver auth SQLi scenario checks failed", report["checks"])
    except Exception as exc:
        error = exc
        report.update({"ok": False, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}", "finishedAt": timestamp()})
        try:
            report["messages"] = request("GET", "/messages", timeout=5.0)
            report["state"] = request("GET", "/state", timeout=5.0)
            report["results"] = request("GET", "/results", timeout=5.0)
        except Exception:
            pass
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
        mock.shutdown()
        lab.shutdown()
        temp_home.cleanup()
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error:
        raise error
    print(f"webserver auth SQLi scenario proof passed: {ARTIFACT}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"webserver auth SQLi scenario proof failed: {exc}", flush=True)
        raise SystemExit(1)
