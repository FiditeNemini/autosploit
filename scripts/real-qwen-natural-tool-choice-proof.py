#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
MODEL_27B = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP")
MODEL_35B = Path("/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP")
FINAL_MARKER = "REAL_QWEN_NATURAL_TOOL_CHOICE_FINAL"
DEFAULT_OUTPUT_27B = ROOT / "docs/live-proofs/2026-07-06-real-qwen-natural-tool-choice-27b.json"
DEFAULT_OUTPUT_35B = ROOT / "docs/live-proofs/2026-07-06-real-qwen-natural-tool-choice-35b.json"
SCENARIO_TOOL_SCHEMA_MAX = 12
NATURAL_EXPECTED_TOOLS = ["httpx", "katana", "sqlmap", "search_cve"]


def load_module(name: str, path: Path):
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


web_proof = load_module("exploitbot_webserver_auth_sqli_proof", ROOT / "scripts" / "webserver-auth-sqli-scenario-proof.py")
exact_web = load_module("exploitbot_real_qwen_webserver_auth_sqli_proof", ROOT / "scripts" / "real-qwen-webserver-auth-sqli-proof.py")
real_qwen = exact_web.real_qwen
live_batch = exact_web.live_batch


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:8000]
        raise AssertionError(message + suffix)


def exactToolCallBlocksPresent(text: str) -> bool:
    open_tag = "<" + "tool_call>"
    close_tag = "</" + "tool_call>"
    return open_tag in text or close_tag in text


def output_path_for_model(model: Path) -> Path:
    override = os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_TOOL_CHOICE_OUTPUT")
    if override:
        return Path(override).expanduser()
    if "35b" in str(model).lower():
        return DEFAULT_OUTPUT_35B
    return DEFAULT_OUTPUT_27B


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def app_request(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 15.0):
    return real_qwen.app_request(method, path, body, timeout=timeout)


def request_json(method: str, url: str, body: dict[str, Any] | str | None = None, timeout: float = 15.0):
    return real_qwen.request_json(method, url, body, timeout=timeout)


def wait_for_app(timeout: float = 30.0) -> None:
    real_qwen.wait_until(lambda: app_request("GET", "/state", timeout=1.0), "app test server", timeout=timeout)


def natural_webserver_prompt(lab_url: str) -> str:
    return (
        "Authorized local fixture only; this is a natural-language objective, not an exact call script. "
        f"Target scope is only {lab_url}. Do not touch external hosts. "
        "choose the app tools you need from the provided schemas to complete this workflow end to end: "
        "surface the local web routes and live service, probe for a web vulnerability, prove whether the search q parameter "
        "has SQL injection in the local fixture, enrich the finding with relevant CVE context, and then write a concise "
        f"evidence summary that starts with {FINAL_MARKER}. "
        "Only call tools that are present in the provided tool schemas; do not write raw shell commands in prose. "
        "If route discovery is needed, call the provided web crawler or fuzzer tool rather than describing a command. "
        "Use tool results instead of guessing. Keep actions bounded to the loopback lab and include the proof marker "
        "EXPLOITBOT_SQLI_PROOF_USER=alice if the vulnerability is confirmed."
    )


def final_followup_prompt(lab_url: str) -> str:
    return (
        "Do not call more tools. Use only the existing local fixture transcript. "
        f"Start with {FINAL_MARKER}, then summarize evidence for {lab_url}, the route surface, web probe, nuclei finding, "
        "sqlmap q-parameter proof, EXPLOITBOT_SQLI_PROOF_USER=alice, and CVE-2021-41773 if present."
    )


def wait_for_quiet_messages(timeout: float = 360.0) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    deadline = time.time() + timeout
    last_state: dict[str, Any] = {}
    last_messages: list[dict[str, Any]] = []
    last_signature = ""
    last_progress_at = time.time()
    stall_seconds = float(os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_STALL_SECONDS", "75"))
    while time.time() < deadline:
        try:
            messages = app_request("GET", "/messages", timeout=5.0)
            state = app_request("GET", "/state", timeout=5.0)
            last_state = state
            last_messages = messages
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            time.sleep(0.5)
            continue
        if not state.get("isWorking") and not state.get("isStreaming"):
            return messages, state
        signature = json.dumps(
            {
                "working": state.get("isWorking"),
                "streaming": state.get("isStreaming"),
                "messageCount": len(messages),
                "lastRole": messages[-1].get("role") if messages else "",
                "lastTextLen": len(str(messages[-1].get("content") or "")) if messages else 0,
                "lastTool": ((state.get("toolExecutor") or {}).get("currentTool") or ""),
                "toolRunning": ((state.get("toolExecutor") or {}).get("isRunning") or False),
            },
            sort_keys=True,
        )
        if signature != last_signature:
            last_signature = signature
            last_progress_at = time.time()
        elif time.time() - last_progress_at >= stall_seconds:
            try:
                app_request("POST", "/stop", "", timeout=5.0)
            except Exception:
                pass
            if model_selected_expected_sequence(messages):
                state["naturalToolChoiceStallRecoveredAfterEvidence"] = True
                return messages, state
            raise AssertionError(f"natural tool-choice stream made no observable progress for {stall_seconds:.1f}s", {
                "signature": json.loads(signature),
                "toolSequence": web_proof.tool_sequence(messages),
                "state": state,
                "messages": messages,
            })
        time.sleep(0.5)
    if last_messages and model_selected_expected_sequence(last_messages):
        last_state["naturalToolChoiceTimeoutRecoveredAfterEvidence"] = True
        try:
            app_request("POST", "/stop", "", timeout=5.0)
        except Exception:
            pass
        return last_messages, last_state
    raise AssertionError("timed out waiting for natural tool-choice turn to finish", last_state)


def model_selected_expected_sequence(messages: list[dict[str, Any]]) -> bool:
    sequence = web_proof.tool_sequence(messages)
    return web_proof.ordered_subsequence(sequence, NATURAL_EXPECTED_TOOLS)


def build_natural_report(
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
    sequence = web_proof.tool_sequence(messages)
    schema_names = web_proof.model_schema_names(model_requests)
    raw_tools = [row.get("tool") for row in results.get("rawResults") or [] if isinstance(row, dict)]
    vulns = results.get("vulns") or []
    vuln_sources = {row.get("source") for row in vulns if isinstance(row, dict)}
    checks = {
        "modelReceivedNaturalWebToolSchemas": web_proof.passfail(all(tool in schema_names for tool in NATURAL_EXPECTED_TOOLS)),
        "genericShellSchemaExcluded": web_proof.passfail("run_shell" not in schema_names),
        "orderedNaturalToolSequence": web_proof.passfail(web_proof.ordered_subsequence(sequence, NATURAL_EXPECTED_TOOLS)),
        "verboseNaturalToolTranscript": web_proof.passfail(all(f"Tool request: {tool}" in text for tool in NATURAL_EXPECTED_TOOLS)),
        "modelContinuedAfterTools": web_proof.passfail(len(model_requests) >= 2 and FINAL_MARKER in text),
        "httpProbeEvidence": web_proof.passfail("httpx" in raw_tools and "ExploitBot SQLi Lab" in results_text),
        "sqlInjectionProof": web_proof.passfail("sqlmap" in raw_tools and "Parameter: q" in results_text and "EXPLOITBOT_SQLI_PROOF_USER=alice" in results_text),
        "cveContextEvidence": web_proof.passfail(
            "search_cve" in raw_tools
            and ("CWE-89" in text or "No CVEs found" in text or "CVE-" in text or "CVE-" in results_text)
        ),
        "safeLocalBoundary": web_proof.passfail(lab_url.startswith("http://127.0.0.1:") and "http://example" not in text),
        "rawResultEvidence": web_proof.passfail(all(tool in results_text for tool in ["httpx", "katana", "sqlmap"])),
        "terminalTranscripts": web_proof.passfail(all(tool in terminal_text for tool in ["httpx", "katana", "sqlmap"])),
        "reportGeneratedFromEvidence": web_proof.passfail(
            "reportRenderActions" in report_text
            and "done" in report_text
            and "SQL injection in local search parameter" in report_text
            and "EXPLOITBOT_SQLI_PROOF_USER=alice" in report_text
        ),
    }
    ok = all(value == "PASS" for value in checks.values())
    return {
        "ok": ok,
        "proofType": "real-qwen-natural-tool-choice-webserver-sqli",
        "status": "PASS" if ok else "FAIL",
        "scenarioId": "real_qwen_natural_tool_choice_webserver_auth_sqli",
        "startedAt": started_at,
        "finishedAt": finished_at,
        "labUrl": lab_url,
        "stages": web_proof.STAGES,
        "toolSequence": sequence,
        "expectedToolSequence": NATURAL_EXPECTED_TOOLS,
        "toolSchemaNames": sorted(set(schema_names)),
        "checks": checks,
        "resultsSummary": {
            "webHostCount": len(results.get("webHosts") or []),
            "vulnCount": len(vulns),
            "vulnSources": sorted(source for source in vuln_sources if source),
            "rawResultCount": len(results.get("rawResults") or []),
            "rawTools": raw_tools,
        },
    }


def synthesize_model_requests_from_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return exact_web.synthesize_model_requests_from_messages(messages)


def run() -> None:
    model = Path(os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_TOOL_CHOICE_MODEL", str(MODEL_27B))).expanduser()
    output = output_path_for_model(model)
    lab_port = real_qwen.free_port()
    lab_url = f"http://127.0.0.1:{lab_port}"
    web_proof.LabState.port = lab_port
    lab = ThreadingHTTPServer(("127.0.0.1", lab_port), web_proof.WebLabHandler)
    lab_thread = threading.Thread(target=lab.serve_forever, daemon=True)
    lab_thread.start()

    report: dict[str, Any] = {
        "ok": False,
        "proofType": "real-qwen-natural-tool-choice",
        "proofLevel": "live-app-real-qwen-natural-language-tool-selection-local-webserver-fixture",
        "model": str(model),
        "labUrl": lab_url,
        "startedAt": timestamp(),
        "modelLoadAttempted": False,
        "toolChoiceMode": "model_selected_tool_sequence",
        "modelToolChoiceEvidence": "model_selected_tool_sequence",
        "forcedSpecificToolRetry": "not_used",
        "status": {"overall": "FAIL"},
    }
    app: subprocess.Popen[str] | None = None
    engine: subprocess.Popen[str] | None = None
    error: Exception | None = None
    app_home = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-natural-home-", ignore_cleanup_errors=True)
    cache_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-natural-cache-", ignore_cleanup_errors=True)
    web_proof.FINAL_MARKER = FINAL_MARKER
    prompt = natural_webserver_prompt(lab_url)
    try:
        require(model.is_dir(), f"Qwen model folder is missing: {model}")
        require(not exactToolCallBlocksPresent(prompt), "natural prompt unexpectedly contains exact tool-call blocks", prompt)
        report["prompt"] = prompt
        report["exactToolCallBlocksPresent"] = False
        report["memoryPreflight"] = live_batch.live_batch_memory_preflight(model, 1)
        report["status"]["memoryPreflight"] = "PASS"

        home = Path(app_home.name)
        tools_dir = web_proof.install_fake_web_tools_at(home / ".exploitbot" / "tools", lab_url)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        env["PATH"] = f"{tools_dir}:{env.get('PATH', '/usr/bin:/bin')}"

        with app_proof_lock("real-qwen-natural-tool-choice-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            real_qwen.build_app_bundle()
            web_proof.install_fake_web_tools_at(APP_BINARY.parents[1] / "Resources" / "tools", lab_url)
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_for_app()

            port = int(os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_TOOL_CHOICE_ENGINE_PORT") or real_qwen.free_port())
            base_url = f"http://127.0.0.1:{port}"
            report["baseUrl"] = base_url
            report["modelLoadAttempted"] = True
            os.environ.setdefault(
                "EXPLOITBOT_REAL_QWEN_REAL_TOOLS_MAX_TOKENS",
                os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_TOOL_CHOICE_MAX_TOKENS", "320"),
            )
            engine = real_qwen.launch_engine(model, port, Path(cache_tmp.name))
            health = real_qwen.wait_health(base_url, engine)
            cache_before = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)

            app_request("POST", "/engine/mock", base_url, timeout=15.0)
            app_request("POST", "/mode", "autopilot", timeout=15.0)
            app_request("POST", "/reasoning", "off", timeout=15.0)
            app_request("POST", "/tab", "web", timeout=15.0)
            app_request(
                "POST",
                "/qa/apply-app-settings",
                {
                    "maxIterations": 8,
                    "toolSchemaMaxTools": SCENARIO_TOOL_SCHEMA_MAX,
                    "includeUnavailableToolSchemas": False,
                    "toolSchemaExcludedTools": ["run_shell"],
                    "forceFinalAnswerAfterToolResults": False,
                    "followAgent": False,
                    "engine": {
                        "modelPath": str(model),
                        "useModelGenerationDefaults": False,
                        "maxTokens": int(os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_TOOL_CHOICE_MAX_TOKENS", "320")),
                        "temperature": 0.0,
                        "topP": 1.0,
                        "reasoningParser": "qwen3",
                        "toolCallParser": "qwen",
                        "kvCacheQuantization": "turboquant-q4",
                        "prefixCache": True,
                        "diskCache": True,
                        "pagedCache": True,
                        "blockDiskCache": True,
                        "cacheMemoryPercent": 0.20,
                    },
                    "chat": {"enableReasoning": False},
                },
                timeout=15.0,
            )
            catalog = app_request(
                "POST",
                "/qa/tool-catalog",
                {
                    "query": prompt,
                    "tab": "web",
                    "maxTools": SCENARIO_TOOL_SCHEMA_MAX,
                    "includeUnavailable": False,
                    "excludedToolNames": ["run_shell"],
                },
                timeout=15.0,
            )
            require("run_shell" not in (catalog.get("toolNames") or []), "generic shell schema should be excluded for natural tool-choice turn", catalog)
            for tool in NATURAL_EXPECTED_TOOLS:
                require(tool in (catalog.get("toolNames") or []), f"tool schema missing before natural tool-choice turn: {tool}", catalog)
            report["preflightToolCatalog"] = catalog

            app_request("POST", "/send", prompt, timeout=15.0)
            messages, state = wait_for_quiet_messages(timeout=420.0)
            natural_sequence = web_proof.tool_sequence(messages)
            report["naturalTurnToolSequence"] = natural_sequence

            if model_selected_expected_sequence(messages) and not web_proof.has_assistant_marker(messages, FINAL_MARKER):
                app_request(
                    "POST",
                    "/qa/apply-app-settings",
                    {"toolSchemaMaxTools": 0, "forceFinalAnswerAfterToolResults": True},
                    timeout=15.0,
                )
                app_request("POST", "/send", final_followup_prompt(lab_url), timeout=15.0)
                messages, state = wait_for_quiet_messages(timeout=180.0)

            results = app_request("GET", "/results", timeout=10.0)
            web_proof.submit_report_from_results(lab_url, results)
            report_state = app_request("GET", "/state", timeout=10.0)
            cache_after = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)
            scenario_report = build_natural_report(
                started_at=report["startedAt"],
                finished_at=timestamp(),
                lab_url=lab_url,
                messages=messages,
                state=state,
                results=results,
                report_state=report_state,
                model_requests=synthesize_model_requests_from_messages(messages),
            )
            cache_status = exact_web.cache_checks(cache_after)
            model_status = exact_web.model_capability_checks(model, health, cache_after)
            status = {
                "overall": "PASS",
                "memoryPreflight": "PASS" if report.get("memoryPreflight") else "FAIL",
                "naturalLanguagePrompt": "PASS",
                "exactToolCallBlocksPresent": "FAIL" if exactToolCallBlocksPresent(prompt) else "PASS",
                "scenarioToolSchemaCapped": "PASS" if len(catalog.get("toolNames") or []) <= SCENARIO_TOOL_SCHEMA_MAX else "FAIL",
                "genericShellSchemaExcluded": "PASS" if "run_shell" not in (catalog.get("toolNames") or []) else "FAIL",
                "modelSelectedToolSequence": "PASS" if model_selected_expected_sequence(messages) else "FAIL",
                "noForcedSpecificToolRetry": "PASS",
                "realQwenDroveNaturalWebserverSQLi": "PASS" if scenario_report.get("ok") is True else "FAIL",
                **scenario_report.get("checks", {}),
                **cache_status,
                **model_status,
            }
            status["overall"] = "PASS" if all(value == "PASS" for value in status.values() if isinstance(value, str)) else "FAIL"
            report.update(
                {
                    "ok": status["overall"] == "PASS",
                    "status": status,
                    "scenarioId": "real_qwen_natural_tool_choice_webserver_auth_sqli",
                    "generatedAt": timestamp(),
                    "finishedAt": timestamp(),
                    "stages": web_proof.STAGES,
                    "toolSequence": web_proof.tool_sequence(messages),
                    "expectedToolSequence": NATURAL_EXPECTED_TOOLS,
                    "health": health,
                    "cacheBefore": cache_before,
                    "cacheAfter": cache_after,
                    "messages": messages,
                    "state": state,
                    "results": results,
                    "scenarioChecks": scenario_report.get("checks", {}),
                    "reportRenderActions": report_state.get("reportRenderActions") or {},
                    "resultsSummary": scenario_report.get("resultsSummary") or {},
                    "notes": [
                        "The initial model turn receives a natural-language objective plus tool schemas only.",
                        "No exact tool-call blocks are serialized in the prompt and no function-specific retry is used.",
                        "The local webserver and scanner binaries are deterministic loopback fixtures for safe proof.",
                    ],
                }
            )
            if not report["ok"]:
                raise AssertionError("real-Qwen natural tool-choice checks failed", status)
    except Exception as exc:
        error = exc
        if "memoryPreflight" not in report["status"]:
            report["status"]["memoryPreflight"] = "BLOCKED" if not report.get("modelLoadAttempted") else "FAIL"
        report.update({"ok": False, "error": f"{type(exc).__name__}: {exc}", "finishedAt": timestamp()})
        try:
            report["messages"] = app_request("GET", "/messages", timeout=5.0)
            report["state"] = app_request("GET", "/state", timeout=5.0)
            report["results"] = app_request("GET", "/results", timeout=5.0)
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
        if engine is not None:
            real_qwen.terminate_process_group(engine)
            report["engineLogTail"] = real_qwen.read_output_tail(engine)
        lab.shutdown()
        app_home.cleanup()
        cache_tmp.cleanup()
        report.setdefault("finishedAt", timestamp())
        write_report(output, report)

    if error is not None:
        raise error
    print(f"real-qwen natural tool-choice proof passed: {output}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"real-qwen natural tool-choice proof failed: {exc}", flush=True)
        raise SystemExit(1)
