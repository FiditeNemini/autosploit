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
MOCK_ENGINE = "http://127.0.0.1:19027"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-network-credential-post-scenario.json"
FIXTURE_PROOF = ROOT / "scripts/autonomous-scenario-fixture-setup-proof.py"
STAGES = ["surface", "probe", "prove", "exploit_or_validate", "evidence", "report"]
EXPECTED_TOOLS = ["nmap", "httpx", "hydra", "netexec", "run_shell", "linpeas"]
FINAL_MARKER = "NETWORK_CREDENTIAL_POST_FINAL"


class MockState:
    lock = threading.Lock()
    requests: list[dict[str, Any]] = []
    lab_url = ""
    lab_host = "127.0.0.1"
    lab_port = 0
    password_file = ""


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
            self._json({"status": "ok", "model": "mock-network-credential-post"})
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
            lab_port = MockState.lab_port
            password_file = MockState.password_file

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        if turn == 1:
            tool_calls = [
                ("call_network_nmap", "nmap", {"target": "127.0.0.1", "ports": str(lab_port), "service_detection": True}),
                ("call_network_httpx", "httpx", {"targets": lab_url, "status_code": True, "title": True, "tech_detect": True}),
                (
                    "call_network_hydra",
                    "hydra",
                    {
                        "target": "127.0.0.1",
                        "protocol": "http-get",
                        "port": lab_port,
                        "path": "/login?user=demo&pass=demo",
                        "username": "demo",
                        "password_file": password_file,
                    },
                ),
                ("call_network_netexec", "netexec", {"target": "127.0.0.1", "protocol": "smb", "shares": True, "timeout": 2, "smb_timeout": 2}),
                ("call_network_post_check", "run_shell", {"command": f"curl -sS {lab_url}/post-check"}),
                ("call_network_linpeas", "linpeas", {"flags": "-q"}),
            ]
            events: list[dict[str, Any]] = [
                {"choices": [{"delta": {"content": "Starting local network credential and post-check workflow."}}]},
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
                                    f"{FINAL_MARKER}: discovered the loopback network fixture, validated only the seeded "
                                    "demo credential, captured EXPLOITBOT_NETWORK_LOGIN_OK and EXPLOITBOT_LINPEAS_FIXTURE_OK, "
                                    "recorded linpeas host attribution, and queued the report evidence."
                                )
                            }
                        }
                    ]
                }
            ]

        events.append(
            {
                "usage": {
                    "prompt_tokens": 330 + turn,
                    "completion_tokens": 76,
                    "prompt_tokens_details": {"cached_tokens": 26 * turn},
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


def install_fake_network_tools_at(tools_dir: Path, lab_url: str) -> Path:
    tools_dir.mkdir(parents=True, exist_ok=True)
    port = lab_url.rsplit(":", 1)[-1]
    write_executable(
        tools_dir / "nmap",
        f"""#!/usr/bin/python3
print("{port}/tcp open http ExploitBot demo service 1.0")
""",
    )
    write_executable(
        tools_dir / "httpx",
        f"""#!/usr/bin/python3
import json
print(json.dumps({{"url": "{lab_url}", "input": "{lab_url}", "status_code": 200, "title": "ExploitBot network fixture", "webserver": "ExploitBotDemo/1.0", "tech": ["python", "network-fixture"]}}))
""",
    )
    write_executable(
        tools_dir / "hydra",
        f"""#!/usr/bin/python3
print("[{port}][http-get] host: 127.0.0.1   login: demo   password: demo   EXPLOITBOT_NETWORK_LOGIN_OK")
""",
    )
    write_executable(
        tools_dir / "netexec",
        """#!/usr/bin/python3
print("SMB  127.0.0.1  445  QA-NETWORK  [*] Windows Server 2019 signing:false")
""",
    )
    write_executable(
        tools_dir / "linpeas.sh",
        """#!/usr/bin/python3
print("Hostname: exploitbot-network-fixture")
print("User: demo")
print("EXPLOITBOT_LINPEAS_FIXTURE_OK")
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
    post_rows = results.get("postAttribution") or []
    checks = {
        "modelReceivedNetworkToolSchemas": passfail(all(tool in schema_names for tool in EXPECTED_TOOLS)),
        "orderedToolSequence": passfail(ordered_subsequence(sequence, EXPECTED_TOOLS)),
        "verboseToolTranscript": passfail(all(f"Tool request: {tool}" in text for tool in EXPECTED_TOOLS)),
        "modelContinuedAfterTools": passfail(len(model_requests) >= 2 and FINAL_MARKER in text),
        "networkSurfaceEvidence": passfail("ExploitBot demo service 1.0" in text or "ExploitBot demo service 1.0" in results_text),
        "httpProbeEvidence": passfail(
            "httpx" in raw_tools
            and ("ExploitBot network fixture" in results_text or '"status_code":200' in results_text or "status_code" in results_text)
        ),
        "credentialProof": passfail("hydra" in vuln_sources and "EXPLOITBOT_NETWORK_LOGIN_OK" in (text + results_text)),
        "networkHostEvidence": passfail("netexec" in text and "QA-NETWORK" in results_text),
        "postCheckProof": passfail("EXPLOITBOT_LINPEAS_FIXTURE_OK" in (text + results_text)),
        "postAttributionEvidence": passfail(any(row.get("label") == "linpeas-host" and row.get("host") == "exploitbot-network-fixture" for row in post_rows)),
        "safeLocalBoundary": passfail(lab_url.startswith("http://127.0.0.1:")),
        "rawResultEvidence": passfail(all(tool in raw_tools for tool in EXPECTED_TOOLS)),
        "terminalTranscripts": passfail(all(tool in terminal_text for tool in ["nmap", "hydra", "netexec", "run_shell", "linpeas"])),
        "reportGeneratedFromEvidence": passfail(
            "reportRenderActions" in report_text
            and "done" in report_text
            and "Network credential and post-check in local fixture" in report_text
            and "EXPLOITBOT_NETWORK_LOGIN_OK" in report_text
            and "EXPLOITBOT_LINPEAS_FIXTURE_OK" in report_text
        ),
    }
    ok = all(value == "PASS" for value in checks.values())
    return {
        "ok": ok,
        "proofType": "network-credential-post-scenario-live",
        "proofLevel": "live-app-mock-engine-real-tool-executor-fake-local-network-tools",
        "status": "PASS" if ok else "FAIL",
        "scenarioId": "network_service_credential_post_chain",
        "generatedAt": finished_at,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "labUrl": lab_url,
        "stages": STAGES,
        "stageEvidence": {
            "surface": ["nmap loopback service discovery", "httpx loopback web probe"],
            "probe": ["hydra seeded credential validation", "netexec local network host parser evidence"],
            "prove": ["EXPLOITBOT_NETWORK_LOGIN_OK", "QA-NETWORK host evidence"],
            "exploit_or_validate": ["run_shell post-check and linpeas fixture output only"],
            "evidence": ["/messages tool cards", "/results rawResults/vulns/networkHosts/postAttribution", "/state terminal transcripts"],
            "report": ["/qa/finding-wizard-submit", "/qa/report-generate-action"],
        },
        "toolSequence": sequence,
        "expectedToolSequence": EXPECTED_TOOLS,
        "toolSchemaNames": sorted(set(schema_names)),
        "checks": checks,
        "messages": messages,
        "resultsSummary": {
            "portCount": len(results.get("ports") or []),
            "networkHostEvidenceMode": "rawResultsAndTerminalTranscript",
            "vulnCount": len(vulns),
            "vulnSources": sorted(source for source in vuln_sources if source),
            "postAttributionCount": len(post_rows),
            "rawResultCount": len(results.get("rawResults") or []),
            "rawTools": raw_tools,
        },
        "reportRenderActions": report_state.get("reportRenderActions") or {},
        "notes": [
            "Scenario uses a loopback network fixture and deterministic local network/post tool shims on isolated PATH.",
            "Credential validation is limited to seeded demo/demo fixture credentials.",
            "No external target, lateral movement, host modification, or privileged post-exploitation is performed.",
        ],
    }


def submit_report_from_results(lab_url: str) -> dict[str, Any]:
    created = request(
        "POST",
        "/qa/finding-wizard-submit",
        {
            "title": "Network credential and post-check in local fixture",
            "vulnType": "network_credential_post",
            "target": lab_url,
            "severity": "high",
            "cvss": 8.2,
            "description": "The local network fixture accepts seeded demo credentials and exposes a harmless post-check marker. EXPLOITBOT_NETWORK_LOGIN_OK",
            "impact": "Valid credentials can enable additional post-auth visibility if this pattern exists in a real scoped environment.",
            "remediation": "Disable seeded/demo credentials, enforce lockout and MFA, and restrict post-auth checks to least-privilege service accounts.",
            "cveId": "",
            "evidence": [
                "EXPLOITBOT_NETWORK_LOGIN_OK",
                "EXPLOITBOT_LINPEAS_FIXTURE_OK",
                "hydra demo credential proof",
                "linpeas host attribution exploitbot-network-fixture",
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
    mock = ThreadingHTTPServer(("127.0.0.1", 19027), MockEngineHandler)
    mock_thread = threading.Thread(target=mock.serve_forever, daemon=True)
    mock_thread.start()

    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-network-post-home-", ignore_cleanup_errors=True)
    report: dict[str, Any] = {"ok": False, "proofType": "network-credential-post-scenario-live", "startedAt": started_at}
    error: Exception | None = None
    try:
        fixture_session = fixture_module.build_fixture_session()
        lab_url = fixture_session.target_for("network_service_credential_post_chain")
        lab_port = int(lab_url.rsplit(":", 1)[-1])
        home = Path(temp_home.name)
        password_file = home / "demo-passwords.txt"
        password_file.write_text("demo\n", encoding="utf-8")
        MockState.lab_url = lab_url
        MockState.lab_port = lab_port
        MockState.password_file = str(password_file)
        tools_dir = install_fake_network_tools_at(home / ".exploitbot" / "tools", lab_url)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        env["PATH"] = f"{tools_dir}:{env.get('PATH', '/usr/bin:/bin')}"

        with app_proof_lock("network-credential-post-scenario-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            install_fake_network_tools_at(APP_BINARY.parents[1] / "Resources" / "tools", lab_url)
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_until(lambda: request("GET", "/state", timeout=1.0), "app test server")

            request("POST", "/engine/mock", MOCK_ENGINE)
            request("POST", "/mode", "autopilot")
            request("POST", "/reasoning", "off")
            request("POST", "/tab", "network")
            request("POST", "/qa/apply-app-settings", {"toolSchemaMaxTools": 64, "maxIterations": 8})
            catalog = request(
                "POST",
                "/qa/tool-catalog",
                {
                    "query": "network service credential httpx hydra netexec linpeas post check loopback",
                    "tab": "network",
                    "maxTools": 64,
                    "includeUnavailable": False,
                },
                timeout=15.0,
            )
            for tool in EXPECTED_TOOLS:
                if tool not in (catalog.get("toolNames") or []):
                    raise AssertionError(f"tool schema missing before network/post turn: {tool}: {catalog}")
            report["preflightToolCatalog"] = catalog

            request(
                "POST",
                "/send",
                (
                    "Authorized local network lab only. Use nmap, httpx, hydra, netexec, run_shell, and linpeas "
                    f"against this loopback fixture only: {lab_url}. Discover the service, validate only seeded demo/demo "
                    "credentials, run the harmless post-check endpoint, capture EXPLOITBOT_NETWORK_LOGIN_OK and "
                    f"EXPLOITBOT_LINPEAS_FIXTURE_OK, then summarize with {FINAL_MARKER}."
                ),
            )

            messages = wait_until(
                lambda: (
                    current if has_assistant_marker(current, FINAL_MARKER) else None
                ) if (current := request("GET", "/messages")) else None,
                "network credential/post final answer",
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
                raise AssertionError("network credential/post scenario checks failed", report["checks"])
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
    print(f"network credential/post scenario proof passed: {ARTIFACT}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"network credential/post scenario proof failed: {exc}", flush=True)
        raise SystemExit(1)
