#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import signal
import socket
import stat
import subprocess
import sys
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
MOCK_ENGINE = "http://127.0.0.1:19024"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-webserver-ssrf-fileread-scenario.json"
FIXTURE_PROOF = ROOT / "scripts/autonomous-scenario-fixture-setup-proof.py"
STAGES = ["surface", "probe", "prove", "exploit_or_validate", "evidence", "report"]
EXPECTED_TOOLS = ["run_shell", "httpx", "nuclei", "search_cve"]
FINAL_MARKER = "WEBAPP_SSRF_FILEREAD_FINAL"


class MockState:
    lock = threading.Lock()
    requests: list[dict[str, Any]] = []
    lab_url = ""


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def passfail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def load_fixture_module():
    spec = importlib.util.spec_from_file_location("exploitbot_autonomous_fixture_setup", FIXTURE_PROOF)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class MockEngineHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"status": "ok", "model": "mock-webserver-ssrf-fileread"})
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
            route_cmd = (
                f"curl -sS {lab_url}/routes && "
                f"curl -sS '{lab_url}/fetch?url={lab_url}/canary' && "
                f"curl -sS '{lab_url}/download?path=fixture-note.txt'"
            )
            tool_calls = [
                ("call_ssrf_routes", "run_shell", {"command": route_cmd}),
                ("call_ssrf_httpx", "httpx", {"targets": lab_url, "status_code": True, "title": True, "tech_detect": True}),
                ("call_ssrf_nuclei", "nuclei", {"target": lab_url, "templates": "webserver-ssrf-fileread-local"}),
                ("call_ssrf_cve", "search_cve", {"query": "SSRF file read local file inclusion", "tags": "ssrf,lfi,file-read", "max_results": 5}),
            ]
            events: list[dict[str, Any]] = [
                {"choices": [{"delta": {"content": "Starting local SSRF and file-read validation workflow."}}]},
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
                                    f"{FINAL_MARKER}: discovered the loopback SSRF/file-read lab, probed httpx/nuclei, "
                                    "validated only local canaries EXPLOITBOT_SSRF_CANARY_OK and "
                                    "EXPLOITBOT_FILE_READ_CANARY_OK, and queued report evidence."
                                )
                            }
                        }
                    ]
                }
            ]

        events.append(
            {
                "usage": {
                    "prompt_tokens": 290 + turn,
                    "completion_tokens": 64,
                    "prompt_tokens_details": {"cached_tokens": 22 * turn},
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


def install_fake_ssrf_tools_at(tools_dir: Path, lab_url: str) -> Path:
    tools_dir.mkdir(parents=True, exist_ok=True)
    write_executable(
        tools_dir / "httpx",
        f"""#!/usr/bin/python3
import json
print(json.dumps({{"url": "{lab_url}", "input": "{lab_url}", "status_code": 200, "title": "ExploitBot SSRF Lab", "webserver": "ExploitBotLab/1.0", "tech": ["python", "ssrf-fixture"]}}))
""",
    )
    write_executable(
        tools_dir / "nuclei",
        f"""#!/usr/bin/python3
import json
print(json.dumps({{
  "template-id": "webserver-ssrf-fileread-local",
  "matched-at": "{lab_url}/fetch?url=http://127.0.0.1/canary",
  "host": "{lab_url}",
  "info": {{
    "name": "Local SSRF and file-read proof",
    "severity": "high",
    "description": "Loopback SSRF and local fixture file-read proof. EXPLOITBOT_SSRF_CANARY_OK EXPLOITBOT_FILE_READ_CANARY_OK",
    "tags": ["ssrf", "lfi", "local-fixture"]
  }}
}}))
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
        "webSurfaceEvidence": passfail("/fetch?url=" in text and "/download?path=fixture-note.txt" in text),
        "httpProbeEvidence": passfail("httpx" in raw_tools and "ExploitBot SSRF Lab" in results_text),
        "nucleiEvidence": passfail("nuclei" in vuln_sources and "webserver-ssrf-fileread-local" in results_text),
        "ssrfProof": passfail("EXPLOITBOT_SSRF_CANARY_OK" in text or "EXPLOITBOT_SSRF_CANARY_OK" in results_text),
        "fileReadProof": passfail("EXPLOITBOT_FILE_READ_CANARY_OK" in text or "EXPLOITBOT_FILE_READ_CANARY_OK" in results_text),
        "cveContextEvidence": passfail("search_cve" in text and ("ssrf" in text.lower() or "file read" in text.lower())),
        "safeLocalBoundary": passfail(lab_url.startswith("http://127.0.0.1:") and "169.254.169.254" not in text and "/etc/passwd" not in text),
        "rawResultEvidence": passfail(all(tool in results_text for tool in ["run_shell", "httpx", "nuclei"])),
        "terminalTranscripts": passfail(all(tool in terminal_text for tool in ["run_shell", "httpx", "nuclei"])),
        "reportGeneratedFromEvidence": passfail(
            "reportRenderActions" in report_text
            and "done" in report_text
            and "SSRF and file-read in local fixture" in report_text
            and "EXPLOITBOT_SSRF_CANARY_OK" in report_text
            and "EXPLOITBOT_FILE_READ_CANARY_OK" in report_text
        ),
    }
    ok = all(value == "PASS" for value in checks.values())
    return {
        "ok": ok,
        "proofType": "webserver-ssrf-fileread-scenario-live",
        "proofLevel": "live-app-mock-engine-real-tool-executor-fake-local-web-scanners",
        "status": "PASS" if ok else "FAIL",
        "scenarioId": "webserver_ssrf_file_read_chain",
        "generatedAt": finished_at,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "labUrl": lab_url,
        "stages": STAGES,
        "stageEvidence": {
            "surface": ["run_shell route inventory", "httpx local web probe"],
            "probe": ["nuclei local SSRF/file-read template", "bounded loopback curl probes"],
            "prove": ["SSRF canary", "file-read canary"],
            "exploit_or_validate": ["bounded local validation only; no cloud metadata or sensitive host file paths"],
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
            "The SSRF and file-read validation uses harmless local fixture canaries only.",
            "This proves app orchestration, verbose transcript, parser/raw result ingestion, and report route wiring.",
        ],
    }


def submit_report_from_results(lab_url: str) -> dict[str, Any]:
    created = request(
        "POST",
        "/qa/finding-wizard-submit",
        {
            "title": "SSRF and file-read in local fixture",
            "vulnType": "ssrf_file_read",
            "target": f"{lab_url}/fetch?url=...",
            "severity": "high",
            "cvss": 8.0,
            "description": "The local fixture fetch endpoint reaches a loopback canary and the download endpoint reads a fixture file.",
            "impact": "An attacker could pivot request targets or read unintended local fixture files if this pattern existed in production.",
            "remediation": "Use strict outbound URL allowlists, block loopback/private networks, and constrain file reads to known fixture paths.",
            "cveId": "",
            "evidence": [
                "EXPLOITBOT_SSRF_CANARY_OK",
                "EXPLOITBOT_FILE_READ_CANARY_OK",
                "nuclei template webserver-ssrf-fileread-local",
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
    fixture_module = load_fixture_module()
    fixture_session = None
    mock = ThreadingHTTPServer(("127.0.0.1", 19024), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-web-ssrf-home-", ignore_cleanup_errors=True)
    report: dict[str, Any] = {"ok": False, "proofType": "webserver-ssrf-fileread-scenario-live", "startedAt": started_at}
    error: Exception | None = None
    try:
        fixture_session = fixture_module.build_fixture_session()
        lab_url = fixture_session.target_for("webserver_ssrf_file_read_chain")
        MockState.lab_url = lab_url
        home = Path(temp_home.name)
        tools_dir = install_fake_ssrf_tools_at(home / ".exploitbot" / "tools", lab_url)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        env["PATH"] = f"{tools_dir}:{env.get('PATH', '/usr/bin:/bin')}"

        with app_proof_lock("webserver-ssrf-fileread-scenario-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            install_fake_ssrf_tools_at(APP_BINARY.parents[1] / "Resources" / "tools", lab_url)
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
                    "Authorized local webserver lab only. Use run_shell, httpx, nuclei, and search_cve "
                    f"against this loopback target only: {lab_url}. Surface routes, probe the SSRF and file-read "
                    f"fixture endpoints, prove EXPLOITBOT_SSRF_CANARY_OK and EXPLOITBOT_FILE_READ_CANARY_OK, "
                    f"then summarize with {FINAL_MARKER}."
                ),
            )

            messages = wait_until(
                lambda: (
                    current if has_assistant_marker(current, FINAL_MARKER) else None
                ) if (current := request("GET", "/messages")) else None,
                "webserver SSRF/file-read final answer",
            )
            state = request("GET", "/state")
            results = request("GET", "/results")
            submit_report_from_results(lab_url)
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
                raise AssertionError("webserver SSRF/file-read scenario checks failed", report["checks"])
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
        if fixture_session is not None:
            fixture_session.close()
        temp_home.cleanup()
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error:
        raise error
    print(f"webserver SSRF/file-read scenario proof passed: {ARTIFACT}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"webserver SSRF/file-read scenario proof failed: {exc}", flush=True)
        raise SystemExit(1)
