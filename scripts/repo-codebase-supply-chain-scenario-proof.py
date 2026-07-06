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
MOCK_ENGINE = "http://127.0.0.1:19016"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-repo-codebase-supply-chain-scenario.json"
STAGES = ["surface", "probe", "prove", "exploit_or_validate", "evidence", "report"]
EXPECTED_TOOLS = ["run_shell", "trufflehog", "syft", "grype", "osv_scanner", "search_cve"]
FINAL_MARKER = "REPO_SUPPLY_CHAIN_FINAL"


class MockState:
    lock = threading.Lock()
    requests: list[dict[str, Any]] = []
    repo_path = ""


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
            self._json({"status": "ok", "model": "mock-repo-supply-chain"})
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
            repo = MockState.repo_path

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        if turn == 1:
            events: list[dict[str, Any]] = [
                {"choices": [{"delta": {"content": "Starting local authorized repo/codebase supply-chain workflow."}}]},
            ]
            tool_calls = [
                ("call_repo_surface", "run_shell", {"command": f"find {repo} -maxdepth 2 -type f | sort"}),
                ("call_repo_secret", "trufflehog", {"source_type": "filesystem", "target": repo, "verified_only": False}),
                ("call_repo_sbom", "syft", {"target": repo, "output": "json"}),
                ("call_repo_grype", "grype", {"target": repo, "fail_on": "critical"}),
                ("call_repo_osv", "osv_scanner", {"target": repo, "format": "json"}),
                ("call_repo_cve", "search_cve", {"query": "lodash 4.17.11 CVE", "product": "lodash", "max_results": 5}),
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
                                    f"{FINAL_MARKER}: surfaced repo files, probed secrets/SBOM/dependencies, "
                                    "validated vulnerable lodash and fake leaked token evidence, then queued report evidence."
                                )
                            }
                        }
                    ]
                }
            ]

        events.append(
            {
                "usage": {
                    "prompt_tokens": 320 + turn,
                    "completion_tokens": 60,
                    "prompt_tokens_details": {"cached_tokens": 32 * turn},
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


def request(method: str, path: str, body: dict | str | None = None, timeout: float = 8.0) -> Any:
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def wait_for_app(timeout: float = 20.0) -> None:
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


def wait_until(predicate, label: str, timeout: float = 60.0):
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


def create_repo_fixture(root: Path) -> Path:
    repo = root / "synthetic-vulnerable-repo"
    repo.mkdir(parents=True)
    (repo / "package.json").write_text(
        json.dumps(
            {
                "name": "exploitbot-supply-chain-lab",
                "version": "1.0.0",
                "dependencies": {"lodash": "4.17.11", "minimist": "0.0.8"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / "package-lock.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 2,
                "packages": {
                    "": {"dependencies": {"lodash": "4.17.11"}},
                    "node_modules/lodash": {"version": "4.17.11"},
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / ".env.example").write_text("DEMO_API_TOKEN=EXPLOITBOT_FAKE_TOKEN_DO_NOT_USE\n", encoding="utf-8")
    (repo / "Dockerfile").write_text("FROM node:12-alpine\nCOPY package*.json ./\n", encoding="utf-8")
    return repo


def write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_fake_tools_at(tools_dir: Path) -> Path:
    tools_dir.mkdir(parents=True, exist_ok=True)
    write_executable(
        tools_dir / "trufflehog",
        """#!/usr/bin/python3
import json
print(json.dumps({
  "DetectorName": "Generic API Key",
  "Raw": "EXPLOITBOT_FAKE_TOKEN_DO_NOT_USE",
  "SourceMetadata": {"Data": {"Git": {"file": ".env.example", "repository": "synthetic-vulnerable-repo"}}}
}))
""",
    )
    write_executable(
        tools_dir / "syft",
        """#!/usr/bin/python3
import json
print(json.dumps({
  "artifacts": [
    {"name": "lodash", "version": "4.17.11", "type": "npm"},
    {"name": "minimist", "version": "0.0.8", "type": "npm"}
  ],
  "source": {"type": "directory", "target": "synthetic-vulnerable-repo"}
}))
""",
    )
    write_executable(
        tools_dir / "grype",
        """#!/usr/bin/python3
import json
print(json.dumps({
  "matches": [
    {
      "vulnerability": {"id": "CVE-2021-23337", "severity": "High"},
      "artifact": {"name": "lodash", "version": "4.17.11", "type": "npm"},
      "matchDetails": [{"type": "exact-direct-match"}]
    }
  ]
}))
""",
    )
    write_executable(
        tools_dir / "osv-scanner",
        """#!/usr/bin/python3
import json
print(json.dumps({
  "results": [
    {
      "packageSource": {"path": "package-lock.json"},
      "packages": [
        {"package": {"name": "lodash", "ecosystem": "npm"}, "vulnerabilities": [{"id": "GHSA-35jh-r3h4-6jhm"}]}
      ]
    }
  ]
}))
""",
    )
    return tools_dir


def install_fake_tools(home: Path) -> Path:
    return install_fake_tools_at(home / ".exploitbot" / "tools")


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


def build_report(
    *,
    started_at: str,
    finished_at: str,
    repo_path: str,
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
    sequence = tool_sequence(messages)
    tool_schema_names = []
    for request_payload in model_requests:
        for tool in request_payload.get("tools") or []:
            name = ((tool.get("function") or {}).get("name") or "").strip()
            if name:
                tool_schema_names.append(name)
    lifecycle = state.get("supplyChainLifecycle") or {}
    terminal = ((state.get("terminal") or {}).get("commandTranscripts") or [])
    terminal_text = json.dumps(terminal, sort_keys=True)
    vulns = results.get("vulns") or []
    vuln_sources = {row.get("source") for row in vulns if isinstance(row, dict)}
    vuln_titles = [str(row.get("title") or "") for row in vulns if isinstance(row, dict)]
    checks = {
        "modelReceivedSupplyChainToolSchemas": passfail(all(tool in tool_schema_names for tool in ["run_shell", "trufflehog", "syft", "grype", "osv_scanner", "search_cve"])),
        "orderedToolSequence": passfail(ordered_subsequence(sequence, EXPECTED_TOOLS)),
        "verboseToolTranscript": passfail(all(f"Tool request: {tool}" in text for tool in EXPECTED_TOOLS)),
        "modelContinuedAfterTools": passfail(len(model_requests) >= 2 and FINAL_MARKER in text),
        "repoSurfaceEvidence": passfail("package.json" in text and ".env.example" in text),
        "secretEvidence": passfail("EXPLOITBOT_FAKE_TOKEN_DO_NOT_USE" in results_text and "trufflehog" in results_text),
        "sbomEvidence": passfail("lodash" in results_text and "syft" in results_text),
        "dependencyEvidence": passfail("CVE-2021-23337" in results_text and "GHSA-35jh-r3h4-6jhm" in results_text),
        "dependencyStructuredFindings": passfail(
            {"grype", "osv_scanner"}.issubset(vuln_sources)
            and any("CVE-2021-23337" in title for title in vuln_titles)
            and any("GHSA-35jh-r3h4-6jhm" in title for title in vuln_titles)
        ),
        "rawResultEvidence": passfail(all(tool in results_text for tool in ["trufflehog", "syft", "grype", "osv_scanner"])),
        "supplyChainLifecycle": passfail(all((lifecycle.get(key) or {}).get("status") == "done" for key in ["secrets", "sbom", "dependency", "cve"])),
        "terminalTranscripts": passfail(all(tool in terminal_text for tool in ["trufflehog", "syft", "grype", "osv-scanner"])),
        "reportGeneratedFromEvidence": passfail(
            "reportRenderActions" in report_text
            and "done" in report_text
            and "CVE-2021-23337 vulnerable lodash dependency" in report_text
            and "GHSA-35jh-r3h4-6jhm" in report_text
        ),
    }
    ok = all(value == "PASS" for value in checks.values())
    return {
        "ok": ok,
        "proofType": "repo-codebase-supply-chain-scenario-live",
        "proofLevel": "live-app-mock-engine-real-tool-executor-fake-local-scanners",
        "status": "PASS" if ok else "FAIL",
        "scenarioId": "repo_codebase_supply_chain",
        "generatedAt": finished_at,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "repoPath": repo_path,
        "stages": STAGES,
        "stageEvidence": {
            "surface": ["run_shell find repo fixture"],
            "probe": ["trufflehog secret scan", "syft SBOM inventory"],
            "prove": ["grype CVE match", "osv_scanner GHSA match", "search_cve callback"],
            "exploit_or_validate": ["safe validation only; no external exploitation"],
            "evidence": ["/messages tool cards", "/results rawResults/vulns", "/state terminal transcripts"],
            "report": ["/qa/report-submit-finding", "/qa/report-generate-action"],
        },
        "toolSequence": sequence,
        "expectedToolSequence": EXPECTED_TOOLS,
        "toolSchemaNames": sorted(set(tool_schema_names)),
        "checks": checks,
        "messages": messages,
        "resultsSummary": {
            "vulnCount": len(results.get("vulns") or []),
            "vulnSources": sorted(source for source in vuln_sources if source),
            "vulnTitles": vuln_titles,
            "rawResultCount": len(results.get("rawResults") or []),
            "rawTools": [row.get("tool") for row in results.get("rawResults") or [] if isinstance(row, dict)],
        },
        "supplyChainLifecycle": lifecycle,
        "reportRenderActions": report_state.get("reportRenderActions") or {},
        "notes": [
            "Scenario uses a throwaway local repo and fake local scanner binaries on isolated PATH.",
            "This proves app orchestration, transcript verbosity, parser/raw result ingestion, lifecycle state, and report route wiring.",
            "It is not a fresh real-Qwen proof; real-Qwen rows are aggregated separately by the scenario matrix when present.",
        ],
    }


def write_report(report: dict[str, Any]) -> None:
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run() -> None:
    started_at = timestamp()
    mock = ThreadingHTTPServer(("127.0.0.1", 19016), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-repo-scenario-home-", ignore_cleanup_errors=True)
    temp_repo = tempfile.TemporaryDirectory(prefix="exploitbot-repo-scenario-")
    try:
        home = Path(temp_home.name)
        repo = create_repo_fixture(Path(temp_repo.name))
        MockState.repo_path = str(repo)
        tools_dir = install_fake_tools(home)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        env["PATH"] = f"{tools_dir}:{env.get('PATH', '/usr/bin:/bin')}"

        with app_proof_lock("repo-codebase-supply-chain-scenario-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            install_fake_tools_at(APP_BINARY.parents[1] / "Resources" / "tools")
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_for_app()

            request("POST", "/engine/mock", MOCK_ENGINE)
            request("POST", "/qa/apply-app-settings", {"toolSchemaMaxTools": 64, "maxIterations": 8})
            request("POST", "/mode", "autopilot")
            request("POST", "/tab", "supplyChain")
            request(
                "POST",
                "/send",
                (
                    "Authorized local lab only. Use run_shell and supply-chain tools against this local repo path: "
                    f"{repo}. Surface files, probe for secrets and dependencies, prove vulnerable packages with scanner "
                    f"evidence, validate safely without external exploitation, then summarize evidence with {FINAL_MARKER}."
                ),
            )

            messages = wait_until(
                lambda: (
                    current if has_assistant_marker(current, FINAL_MARKER) else None
                ) if (current := request("GET", "/messages")) else None,
                "repo supply-chain final answer",
            )
            state = request("GET", "/state")
            results = request("GET", "/results")

            grype_vuln = next(
                (
                    row for row in results.get("vulns") or []
                    if isinstance(row, dict) and row.get("source") == "grype"
                ),
                {},
            )
            osv_vuln = next(
                (
                    row for row in results.get("vulns") or []
                    if isinstance(row, dict) and row.get("source") == "osv_scanner"
                ),
                {},
            )
            created = request(
                "POST",
                "/qa/finding-wizard-submit",
                {
                    "title": "CVE-2021-23337 vulnerable lodash dependency",
                    "vulnType": "supply_chain_dependency",
                    "target": grype_vuln.get("target") or str(repo),
                    "severity": "high",
                    "cvss": 8.1,
                    "description": grype_vuln.get("description") or "grype reported lodash 4.17.11 as CVE-2021-23337.",
                    "impact": "A vulnerable dependency can expose application code to known supply-chain attack paths.",
                    "remediation": "Upgrade lodash and rerun grype/osv-scanner until no vulnerable version is reported.",
                    "cveId": "CVE-2021-23337",
                    "evidence": [
                        grype_vuln.get("description") or "grype CVE-2021-23337 lodash evidence",
                        osv_vuln.get("description") or "osv_scanner GHSA-35jh-r3h4-6jhm lodash evidence",
                    ],
                },
            )
            if created.get("ok") is not True:
                raise AssertionError(f"report finding create failed: {created}")
            generated = request("POST", "/qa/report-generate-action", {"template": "Full Report"})
            if generated.get("ok") is not True:
                raise AssertionError(f"report generation failed: {generated}")
            report_state = request("GET", "/state")

            with MockState.lock:
                model_requests = list(MockState.requests)

            report = build_report(
                started_at=started_at,
                finished_at=timestamp(),
                repo_path=str(repo),
                messages=messages,
                state=state,
                results=results,
                report_state=report_state,
                model_requests=model_requests,
            )
            write_report(report)
            if not report["ok"]:
                print(json.dumps(report, indent=2, sort_keys=True))
                raise AssertionError("repo-codebase supply-chain scenario checks failed")
            print(f"repo-codebase supply-chain scenario proof passed: {ARTIFACT}")
    finally:
        mock.shutdown()
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
        temp_home.cleanup()
        temp_repo.cleanup()


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"repo-codebase supply-chain scenario proof failed: {exc}", flush=True)
        raise SystemExit(1)
