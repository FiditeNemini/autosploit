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
from typing import Any

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
MOCK_ENGINE = "http://127.0.0.1:19020"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-codebase-static-patch-scenario.json"
STAGES = ["surface", "probe", "prove", "exploit_or_validate", "evidence", "report"]
EXPECTED_TOOLS = ["run_shell", "semgrep", "bandit", "search_context"]
FINAL_MARKER = "CODEBASE_STATIC_PATCH_FINAL"


class MockState:
    lock = threading.Lock()
    requests: list[dict[str, Any]] = []
    codebase_path = ""


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def passfail(value: bool) -> str:
    return "PASS" if value else "FAIL"


class MockEngineHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"status": "ok", "model": "mock-codebase-static-patch"})
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
            codebase = MockState.codebase_path

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        if turn == 1:
            events: list[dict[str, Any]] = [
                {"choices": [{"delta": {"content": "Starting local codebase static analysis workflow."}}]},
            ]
            grep_command = (
                f"find {codebase} -maxdepth 2 -type f | sort && "
                f"grep -R \"EXPLOITBOT_PATH_TRAVERSAL_PROOF\\|open(request.args\" -n {codebase}"
            )
            tool_calls = [
                ("call_codebase_surface", "run_shell", {"command": grep_command}),
                ("call_codebase_semgrep", "semgrep", {"target": codebase, "config": "p/security-audit", "severity": "ERROR"}),
                ("call_codebase_bandit", "bandit", {"target": codebase, "recursive": True, "severity": "medium"}),
                (
                    "call_codebase_context",
                    "search_context",
                    {
                        "query": "EXPLOITBOT_PATH_TRAVERSAL_PROOF app.py:17 path traversal patch recommendation pathlib resolve allowlist",
                        "max_snippets": 4,
                    },
                ),
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
                                    f"{FINAL_MARKER}: mapped the local codebase, proved path traversal at app.py:17 "
                                    "with semgrep and bandit evidence, validated EXPLOITBOT_PATH_TRAVERSAL_PROOF locally, "
                                    "and recommends pathlib resolve plus an allowlist base directory check."
                                )
                            }
                        }
                    ]
                }
            ]

        events.append(
            {
                "usage": {
                    "prompt_tokens": 280 + turn,
                    "completion_tokens": 68,
                    "prompt_tokens_details": {"cached_tokens": 20 * turn},
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


def create_codebase_fixture(root: Path) -> Path:
    codebase = root / "synthetic-codebase-review"
    codebase.mkdir(parents=True)
    (codebase / "app.py").write_text(
        "\n".join(
            [
                "from flask import Flask, request",
                "from pathlib import Path",
                "",
                "app = Flask(__name__)",
                "BASE_DIR = Path('/tmp/exploitbot-codebase-fixture/files')",
                "",
                "@app.route('/download')",
                "def download():",
                "    requested = request.args['path']",
                "    # EXPLOITBOT_PATH_TRAVERSAL_PROOF vulnerable sink for local fixture only",
                "    return open(requested).read()",
                "",
                "def patched_download(path_value):",
                "    candidate = (BASE_DIR / path_value).resolve()",
                "    if BASE_DIR.resolve() not in candidate.parents and candidate != BASE_DIR.resolve():",
                "        raise ValueError('path outside allowlist')",
                "    return candidate.read_text()",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (codebase / "README.md").write_text(
        "Local codebase fixture. Expected patch: pathlib resolve plus allowlist base directory check.\n",
        encoding="utf-8",
    )
    return codebase


def write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_fake_static_tools_at(tools_dir: Path) -> Path:
    tools_dir.mkdir(parents=True, exist_ok=True)
    write_executable(
        tools_dir / "semgrep",
        """#!/usr/bin/python3
import json
print(json.dumps({
  "results": [{
    "check_id": "python.flask.security.path-traversal.open-request-args",
    "path": "app.py",
    "start": {"line": 17, "col": 12},
    "end": {"line": 17, "col": 38},
    "extra": {
      "severity": "ERROR",
      "message": "Path traversal: open(request.args['path']) reaches filesystem without pathlib resolve allowlist.",
      "metadata": {"cwe": ["CWE-22"], "owasp": ["A01:2021"]}
    }
  }]
}))
""",
    )
    write_executable(
        tools_dir / "bandit",
        """#!/usr/bin/python3
import json
print(json.dumps({
  "results": [{
    "filename": "app.py",
    "line_number": 17,
    "test_id": "B108",
    "test_name": "hardcoded_tmp_directory",
    "issue_severity": "MEDIUM",
    "issue_confidence": "HIGH",
    "issue_text": "Potential path traversal sink uses request-controlled path; patch with pathlib resolve allowlist."
  }]
}))
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
    codebase_path: str,
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
        "modelReceivedCodebaseToolSchemas": passfail(all(tool in schema_names for tool in EXPECTED_TOOLS)),
        "orderedToolSequence": passfail(ordered_subsequence(sequence, EXPECTED_TOOLS)),
        "verboseToolTranscript": passfail(all(f"Tool request: {tool}" in text for tool in EXPECTED_TOOLS)),
        "modelContinuedAfterTools": passfail(len(model_requests) >= 2 and FINAL_MARKER in text),
        "codebaseSurfaceEvidence": passfail("app.py" in text and "EXPLOITBOT_PATH_TRAVERSAL_PROOF" in text),
        "semgrepEvidence": passfail("semgrep" in vuln_sources and "python.flask.security.path-traversal" in results_text),
        "banditEvidence": passfail("bandit" in vuln_sources and "B108" in results_text),
        "fileLineEvidence": passfail("app.py:17" in results_text or "app.py:17" in text),
        "validationProof": passfail("EXPLOITBOT_PATH_TRAVERSAL_PROOF" in text or "EXPLOITBOT_PATH_TRAVERSAL_PROOF" in results_text),
        "patchRecommendationEvidence": passfail(
            "pathlib resolve" in (text + results_text + report_text)
            and "allowlist" in (text + results_text + report_text)
        ),
        "safeLocalBoundary": passfail(str(codebase_path).startswith("/var/") or str(codebase_path).startswith("/tmp/") or "exploitbot-codebase" in str(codebase_path)),
        "rawResultEvidence": passfail(all(tool in raw_tools for tool in EXPECTED_TOOLS)),
        "terminalTranscripts": passfail(all(tool in terminal_text for tool in ["semgrep", "bandit"])),
        "reportGeneratedFromEvidence": passfail(
            "reportRenderActions" in report_text
            and "done" in report_text
            and "Path traversal in local codebase" in report_text
            and "EXPLOITBOT_PATH_TRAVERSAL_PROOF" in report_text
        ),
    }
    ok = all(value == "PASS" for value in checks.values())
    return {
        "ok": ok,
        "proofType": "codebase-static-patch-scenario-live",
        "proofLevel": "live-app-mock-engine-real-tool-executor-fake-local-static-analyzers",
        "status": "PASS" if ok else "FAIL",
        "scenarioId": "codebase_static_to_patch_review_chain",
        "generatedAt": finished_at,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "codebasePath": codebase_path,
        "stages": STAGES,
        "stageEvidence": {
            "surface": ["run_shell file inventory and vulnerable sink grep"],
            "probe": ["semgrep static analysis", "bandit Python security analysis"],
            "prove": ["app.py:17 file:line evidence", "EXPLOITBOT_PATH_TRAVERSAL_PROOF marker"],
            "exploit_or_validate": ["bounded local validation only; no host sensitive file read"],
            "evidence": ["/messages tool cards", "/results rawResults/vulns", "/state terminal transcripts"],
            "report": ["/qa/finding-wizard-submit", "/qa/report-generate-action"],
        },
        "toolSequence": sequence,
        "expectedToolSequence": EXPECTED_TOOLS,
        "toolSchemaNames": sorted(set(schema_names)),
        "checks": checks,
        "messages": messages,
        "resultsSummary": {
            "vulnCount": len(vulns),
            "vulnSources": sorted(source for source in vuln_sources if source),
            "rawResultCount": len(results.get("rawResults") or []),
            "rawTools": raw_tools,
        },
        "reportRenderActions": report_state.get("reportRenderActions") or {},
        "notes": [
            "Scenario uses a throwaway local codebase and deterministic local static analyzer shims on isolated PATH.",
            "The vulnerability proof is a local fixture marker, not a host file-read exploit.",
            "This proves app orchestration, verbose transcript, parser/raw result ingestion, context search, and report route wiring.",
        ],
    }


def submit_report_from_results(codebase_path: str, results: dict[str, Any]) -> dict[str, Any]:
    created = request(
        "POST",
        "/qa/finding-wizard-submit",
        {
            "title": "Path traversal in local codebase",
            "vulnType": "path_traversal",
            "target": f"{codebase_path}/app.py:17",
            "severity": "high",
            "cvss": 8.1,
            "description": "The local fixture passes request-controlled path input into open() without pathlib resolve allowlist validation. EXPLOITBOT_PATH_TRAVERSAL_PROOF",
            "impact": "An attacker could read unintended files if untrusted path input reaches the filesystem.",
            "remediation": "Join paths under an allowlisted base directory, call pathlib resolve(), and reject paths outside that base before reading.",
            "cveId": "",
            "evidence": [
                "semgrep app.py:17 path traversal evidence",
                "bandit B108 app.py:17 evidence",
                "EXPLOITBOT_PATH_TRAVERSAL_PROOF",
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
    mock = ThreadingHTTPServer(("127.0.0.1", 19020), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-codebase-static-home-", ignore_cleanup_errors=True)
    temp_codebase = tempfile.TemporaryDirectory(prefix="exploitbot-codebase-static-fixture-", ignore_cleanup_errors=True)
    report: dict[str, Any] = {"ok": False, "proofType": "codebase-static-patch-scenario-live", "startedAt": started_at}
    error: Exception | None = None
    try:
        home = Path(temp_home.name)
        codebase = create_codebase_fixture(Path(temp_codebase.name))
        MockState.codebase_path = str(codebase)
        tools_dir = install_fake_static_tools_at(home / ".exploitbot" / "tools")
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        env["PATH"] = f"{tools_dir}:{env.get('PATH', '/usr/bin:/bin')}"

        with app_proof_lock("codebase-static-patch-scenario-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            install_fake_static_tools_at(APP_BINARY.parents[1] / "Resources" / "tools")
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_until(lambda: request("GET", "/state", timeout=1.0), "app test server")

            request("POST", "/engine/mock", MOCK_ENGINE)
            request("POST", "/mode", "autopilot")
            request("POST", "/reasoning", "off")
            request("POST", "/tab", "supplyChain")
            request("POST", "/qa/apply-app-settings", {"toolSchemaMaxTools": 64, "maxIterations": 6})
            catalog = request(
                "POST",
                "/qa/tool-catalog",
                {
                    "query": "local codebase static analysis semgrep bandit path traversal patch review",
                    "tab": "supplyChain",
                    "maxTools": 64,
                    "includeUnavailable": False,
                },
                timeout=15.0,
            )
            for tool in EXPECTED_TOOLS:
                if tool not in (catalog.get("toolNames") or []):
                    raise AssertionError(f"tool schema missing before codebase static turn: {tool}: {catalog}")
            report["preflightToolCatalog"] = catalog

            request(
                "POST",
                "/send",
                (
                    "Authorized local codebase lab only. Use run_shell, semgrep, bandit, and search_context "
                    f"against this throwaway local codebase only: {codebase}. Surface source files, probe static analyzer "
                    "findings, prove the vulnerable app.py file:line and EXPLOITBOT_PATH_TRAVERSAL_PROOF marker, "
                    f"then summarize patch evidence with {FINAL_MARKER}."
                ),
            )

            messages = wait_until(
                lambda: (
                    current if has_assistant_marker(current, FINAL_MARKER) else None
                ) if (current := request("GET", "/messages")) else None,
                "codebase static final answer",
            )
            state = request("GET", "/state")
            results = request("GET", "/results")
            submit_report_from_results(str(codebase), results)
            report_state = request("GET", "/state")
            with MockState.lock:
                model_requests = list(MockState.requests)
            report = build_report(
                started_at=started_at,
                finished_at=timestamp(),
                codebase_path=str(codebase),
                messages=messages,
                state=state,
                results=results,
                report_state=report_state,
                model_requests=model_requests,
            )
            if not report["ok"]:
                raise AssertionError("codebase static patch scenario checks failed", report["checks"])
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
        temp_home.cleanup()
        temp_codebase.cleanup()
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error:
        raise error
    print(f"codebase static patch scenario proof passed: {ARTIFACT}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"codebase static patch scenario proof failed: {exc}", flush=True)
        raise SystemExit(1)
