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
MOCK_ENGINE = "http://127.0.0.1:19026"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-container-iac-supply-chain-scenario.json"
FIXTURE_PROOF = ROOT / "scripts/autonomous-scenario-fixture-setup-proof.py"
STAGES = ["surface", "probe", "prove", "exploit_or_validate", "evidence", "report"]
EXPECTED_TOOLS = ["run_shell", "syft", "grype", "trivy", "checkov", "search_cve"]
FINAL_MARKER = "CONTAINER_IAC_SUPPLY_CHAIN_FINAL"


class MockState:
    lock = threading.Lock()
    requests: list[dict[str, Any]] = []
    fixture_path = ""


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
            self._json({"status": "ok", "model": "mock-container-iac-supply-chain"})
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
            fixture_path = MockState.fixture_path

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        if turn == 1:
            surface_cmd = (
                f"find {fixture_path} -maxdepth 3 -type f | sort && "
                f"grep -R \"EXPLOITBOT_CONTAINER_IAC_PROOF\\|nginx:1.16\\|allowPrivilegeEscalation: true\" -n {fixture_path}"
            )
            tool_calls = [
                ("call_container_surface", "run_shell", {"command": surface_cmd}),
                ("call_container_syft", "syft", {"target": fixture_path, "output": "json"}),
                ("call_container_grype", "grype", {"target": fixture_path, "fail_on": "high"}),
                ("call_container_trivy", "trivy", {"target": fixture_path, "scan_type": "fs", "severity": "HIGH,CRITICAL"}),
                ("call_container_checkov", "checkov", {"target": fixture_path, "framework": "kubernetes"}),
                (
                    "call_container_cve",
                    "search_cve",
                    {"query": "CVE-2019-20372 nginx 1.16 container", "tags": "container,nginx,cve", "max_results": 5},
                ),
            ]
            events: list[dict[str, Any]] = [
                {"choices": [{"delta": {"content": "Starting local container and IaC validation workflow."}}]},
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
                                    f"{FINAL_MARKER}: inventoried the local Dockerfile and Kubernetes manifest, "
                                    "proved nginx:1.16 with CVE-2019-20372 through SBOM/vulnerability scanner evidence, "
                                    "proved allowPrivilegeEscalation: true with Trivy/Checkov IaC evidence, and queued a report."
                                )
                            }
                        }
                    ]
                }
            ]

        events.append(
            {
                "usage": {
                    "prompt_tokens": 310 + turn,
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


def install_fake_container_tools_at(tools_dir: Path) -> Path:
    tools_dir.mkdir(parents=True, exist_ok=True)
    write_executable(
        tools_dir / "syft",
        """#!/usr/bin/python3
import json
print(json.dumps({
  "source": {"target": "synthetic-container-iac"},
  "artifacts": [
    {"name": "nginx", "version": "1.16", "type": "deb"},
    {"name": "openssl", "version": "1.1.1", "type": "deb"}
  ]
}))
""",
    )
    write_executable(
        tools_dir / "grype",
        """#!/usr/bin/python3
import json
print(json.dumps({
  "matches": [{
    "vulnerability": {"id": "CVE-2019-20372", "severity": "High"},
    "artifact": {"name": "nginx", "version": "1.16"}
  }]
}))
""",
    )
    write_executable(
        tools_dir / "trivy",
        """#!/usr/bin/python3
import json
print(json.dumps({
  "Results": [
    {
      "Target": "Dockerfile",
      "Vulnerabilities": [{
        "VulnerabilityID": "CVE-2019-20372",
        "PkgName": "nginx",
        "InstalledVersion": "1.16",
        "Severity": "HIGH",
        "Title": "nginx vulnerable image package",
        "Description": "nginx:1.16 package evidence for EXPLOITBOT_CONTAINER_IAC_PROOF"
      }]
    },
    {
      "Target": "k8s/deployment.yaml",
      "Misconfigurations": [{
        "ID": "AVD-KSV-0012",
        "Title": "Container allows privilege escalation",
        "Severity": "HIGH",
        "Message": "allowPrivilegeEscalation: true is present in the local Kubernetes fixture"
      }]
    }
  ]
}))
""",
    )
    write_executable(
        tools_dir / "checkov",
        """#!/usr/bin/python3
import json
print(json.dumps({
  "results": {
    "failed_checks": [{
      "check_id": "CKV_K8S_20",
      "check_name": "Containers should not run with allowPrivilegeEscalation",
      "file_path": "/k8s/deployment.yaml",
      "resource": "Deployment.exploitbot-container-iac-proof.web",
      "severity": "HIGH",
      "guideline": "Set securityContext.allowPrivilegeEscalation to false for the local fixture workload."
    }]
  }
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
    fixture_path: str,
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
        "modelReceivedContainerIacToolSchemas": passfail(all(tool in schema_names for tool in EXPECTED_TOOLS)),
        "orderedToolSequence": passfail(ordered_subsequence(sequence, EXPECTED_TOOLS)),
        "verboseToolTranscript": passfail(all(f"Tool request: {tool}" in text for tool in EXPECTED_TOOLS)),
        "modelContinuedAfterTools": passfail(len(model_requests) >= 2 and FINAL_MARKER in text),
        "containerSurfaceEvidence": passfail("Dockerfile" in text and "nginx:1.16" in text and "EXPLOITBOT_CONTAINER_IAC_PROOF" in text),
        "syftEvidence": passfail("syft" in vuln_sources and "nginx" in results_text and "1.16" in results_text),
        "grypeEvidence": passfail("grype" in vuln_sources and "CVE-2019-20372" in results_text),
        "trivyEvidence": passfail("trivy" in vuln_sources and "CVE-2019-20372" in results_text and "AVD-KSV-0012" in results_text),
        "checkovEvidence": passfail("checkov" in vuln_sources and "CKV_K8S_20" in results_text),
        "iacRiskProof": passfail("allowPrivilegeEscalation: true" in text or "allowPrivilegeEscalation" in results_text),
        "cveContextEvidence": passfail("search_cve" in text and "CVE-2019-20372" in text),
        "safeLocalBoundary": passfail(
            str(fixture_path).startswith("/var/")
            or str(fixture_path).startswith("/tmp/")
            or "autonomous-scenario-fixtures" in str(fixture_path)
        ),
        "rawResultEvidence": passfail(all(tool in raw_tools for tool in EXPECTED_TOOLS)),
        "terminalTranscripts": passfail(all(tool in terminal_text for tool in ["syft", "grype", "trivy", "checkov"])),
        "reportGeneratedFromEvidence": passfail(
            "reportRenderActions" in report_text
            and "done" in report_text
            and "Container and Kubernetes IaC risk in local fixture" in report_text
            and "EXPLOITBOT_CONTAINER_IAC_PROOF" in report_text
            and "CKV_K8S_20" in report_text
        ),
    }
    ok = all(value == "PASS" for value in checks.values())
    return {
        "ok": ok,
        "proofType": "container-iac-supply-chain-scenario-live",
        "proofLevel": "live-app-mock-engine-real-tool-executor-fake-local-container-iac-scanners",
        "status": "PASS" if ok else "FAIL",
        "scenarioId": "container_iac_supply_chain_chain",
        "generatedAt": finished_at,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "fixturePath": fixture_path,
        "stages": STAGES,
        "stageEvidence": {
            "surface": ["run_shell Dockerfile/compose/Kubernetes manifest inventory"],
            "probe": ["syft SBOM", "grype vulnerability scan", "trivy vuln/config scan", "checkov IaC scan"],
            "prove": ["nginx:1.16", "CVE-2019-20372", "CKV_K8S_20", "allowPrivilegeEscalation: true"],
            "exploit_or_validate": ["configuration validation only; no container execution or privilege escalation"],
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
            "Scenario uses a throwaway local container/IaC fixture and deterministic scanner shims on isolated PATH.",
            "No Docker daemon, privileged container, external registry, or external target is used.",
            "This proves app orchestration, verbose transcript, parser/raw result ingestion, CVE context callback, and report route wiring.",
        ],
    }


def submit_report_from_results(fixture_path: str) -> dict[str, Any]:
    created = request(
        "POST",
        "/qa/finding-wizard-submit",
        {
            "title": "Container and Kubernetes IaC risk in local fixture",
            "vulnType": "container_iac_supply_chain",
            "target": f"{fixture_path}/Dockerfile and k8s/deployment.yaml",
            "severity": "high",
            "cvss": 8.0,
            "description": "The local fixture uses nginx:1.16 and permits allowPrivilegeEscalation: true. EXPLOITBOT_CONTAINER_IAC_PROOF",
            "impact": "A vulnerable image tag combined with permissive container security context increases exploit blast radius.",
            "remediation": "Use a patched image tag, pin digest provenance, set allowPrivilegeEscalation false, and enforce least-privilege pod security controls.",
            "cveId": "CVE-2019-20372",
            "evidence": [
                "EXPLOITBOT_CONTAINER_IAC_PROOF",
                "nginx:1.16",
                "CVE-2019-20372",
                "CKV_K8S_20",
                "allowPrivilegeEscalation: true",
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
    mock = ThreadingHTTPServer(("127.0.0.1", 19026), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-container-iac-home-", ignore_cleanup_errors=True)
    report: dict[str, Any] = {"ok": False, "proofType": "container-iac-supply-chain-scenario-live", "startedAt": started_at}
    error: Exception | None = None
    try:
        fixture_session = fixture_module.build_fixture_session()
        fixture_path = fixture_session.target_for("container_iac_supply_chain_chain")
        MockState.fixture_path = fixture_path
        home = Path(temp_home.name)
        tools_dir = install_fake_container_tools_at(home / ".exploitbot" / "tools")
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        env["PATH"] = f"{tools_dir}:{env.get('PATH', '/usr/bin:/bin')}"

        with app_proof_lock("container-iac-supply-chain-scenario-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            install_fake_container_tools_at(APP_BINARY.parents[1] / "Resources" / "tools")
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_until(lambda: request("GET", "/state", timeout=1.0), "app test server")

            request("POST", "/engine/mock", MOCK_ENGINE)
            request("POST", "/mode", "autopilot")
            request("POST", "/reasoning", "off")
            request("POST", "/tab", "supplyChain")
            request("POST", "/qa/apply-app-settings", {"toolSchemaMaxTools": 64, "maxIterations": 8})
            catalog = request(
                "POST",
                "/qa/tool-catalog",
                {
                    "query": "container iac supply chain syft grype trivy checkov kubernetes vulnerable image",
                    "tab": "supplyChain",
                    "maxTools": 64,
                    "includeUnavailable": False,
                },
                timeout=15.0,
            )
            for tool in EXPECTED_TOOLS:
                if tool not in (catalog.get("toolNames") or []):
                    raise AssertionError(f"tool schema missing before container/IaC turn: {tool}: {catalog}")
            report["preflightToolCatalog"] = catalog

            request(
                "POST",
                "/send",
                (
                    "Authorized local container/IaC lab only. Use run_shell, syft, grype, trivy, checkov, and search_cve "
                    f"against this throwaway local fixture only: {fixture_path}. Surface Dockerfile and Kubernetes files, "
                    "prove EXPLOITBOT_CONTAINER_IAC_PROOF, nginx:1.16, CVE-2019-20372, CKV_K8S_20, and "
                    f"allowPrivilegeEscalation: true, then summarize with {FINAL_MARKER}."
                ),
            )

            messages = wait_until(
                lambda: (
                    current if has_assistant_marker(current, FINAL_MARKER) else None
                ) if (current := request("GET", "/messages")) else None,
                "container/IaC final answer",
            )
            state = request("GET", "/state")
            results = request("GET", "/results")
            submit_report_from_results(fixture_path)
            report_state = request("GET", "/state")
            with MockState.lock:
                model_requests = list(MockState.requests)
            report = build_report(
                started_at=started_at,
                finished_at=timestamp(),
                fixture_path=fixture_path,
                messages=messages,
                state=state,
                results=results,
                report_state=report_state,
                model_requests=model_requests,
            )
            if not report["ok"]:
                raise AssertionError("container/IaC supply-chain scenario checks failed", report["checks"])
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
    print(f"container/IaC supply-chain scenario proof passed: {ARTIFACT}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"container/IaC supply-chain scenario proof failed: {exc}", flush=True)
        raise SystemExit(1)
