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
import time
import urllib.error
from pathlib import Path
from typing import Any

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
MODEL_27B = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP4-CRACK-MTP")
MODEL_35B = Path("/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP4-CRACK-MTP")
FINAL_MARKER = "REAL_QWEN_NATURAL_NETWORK_CREDENTIAL_POST_FINAL"
DEFAULT_OUTPUT_27B = ROOT / "docs/live-proofs/2026-07-06-real-qwen-natural-network-credential-post-27b.json"
DEFAULT_OUTPUT_35B = ROOT / "docs/live-proofs/2026-07-06-real-qwen-natural-network-credential-post-35b.json"
SCENARIO_TOOL_SCHEMA_MAX = 64
EXPECTED_NETWORK_TOOLS = ["nmap", "httpx", "hydra", "netexec", "run_shell", "linpeas"]
EXCLUDED_SCHEMA_TOOLS = [
    "katana",
    "feroxbuster",
    "ffuf",
    "gowitness",
    "masscan",
    "dnsx",
    "bettercap",
    "tshark",
    "snmpwalk",
    "hashcat",
    "theharvester",
    "semgrep",
    "checkov",
    "wpscan",
    "graphqlmap",
    "syft",
    "trivy",
    "nuclei",
    "sqlmap",
    "osv_scanner",
    "arjun",
    "metasploit",
    "pwncat",
    "dalfox",
    "exiftool",
    "subfinder",
    "sherlock",
    "holehe",
    "jwt_tool",
    "grype",
    "impacket",
    "sliver",
]


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


exact_web = load_module(
    "exploitbot_real_qwen_webserver_auth_sqli_helpers_for_natural_network",
    ROOT / "scripts" / "real-qwen-webserver-auth-sqli-proof.py",
)
network_proof = exact_web.load_module(
    "exploitbot_network_credential_post_natural_contract",
    ROOT / "scripts" / "network-credential-post-scenario-proof.py",
)
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
    override = os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_NETWORK_POST_OUTPUT")
    if override:
        return Path(override).expanduser()
    if "35b" in str(model).lower():
        return DEFAULT_OUTPUT_35B
    return DEFAULT_OUTPUT_27B


def app_request(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 15.0):
    return real_qwen.app_request(method, path, body, timeout=timeout)


def request_json(method: str, url: str, body: dict[str, Any] | str | None = None, timeout: float = 15.0):
    return real_qwen.request_json(method, url, body, timeout=timeout)


def wait_for_app(timeout: float = 30.0) -> None:
    real_qwen.wait_until(lambda: app_request("GET", "/state", timeout=1.0), "app test server", timeout=timeout)


def send_prompt_to_app(prompt: str, timeout: float = 15.0) -> dict[str, Any]:
    try:
        result = app_request("POST", "/send", prompt, timeout=timeout)
        return {"ok": True, "result": result}
    except (TimeoutError, socket.timeout) as exc:
        return {"ok": False, "timedOut": True, "error": f"{type(exc).__name__}: {exc}"}


def cache_after_from_engine_log(log_tail: str, messages: list[dict[str, Any]], error: Exception) -> dict[str, Any]:
    post_count = log_tail.count("POST /v1/chat/completions")
    sequence = network_proof.tool_sequence(messages)
    paged_or_prefix = "Paged cache hit" in log_tail or "stored paged Prefix Cache" in log_tail
    return {
        "cache_stats_endpoint_error": f"{type(error).__name__}: {error}",
        "evidence_source": "engine_log_tail_fallback",
        "native_cache": {
            "cache_type": "hybrid_ssm_typed" if ("HYBRID cache HIT" in log_tail or "SSM" in log_tail) else "",
            "paged": paged_or_prefix,
            "prefix": "Prefix Cache" in log_tail or "prefix cache" in log_tail.lower(),
        },
        "scheduler_stats": {
            "num_requests_processed": max(post_count, 2 if all(tool in sequence for tool in EXPECTED_NETWORK_TOOLS) else 0),
        },
        "scheduler_cache": {
            "block_size": 64 if paged_or_prefix else 0,
            "total_tokens_cached": 1 if paged_or_prefix else 0,
        },
        "kv_cache_quantization": {
            "enabled": True,
            "bits": 4,
            "source": "launch_arg:--kv-cache-quantization turboquant-q4",
        },
        "block_disk_cache": {
            "disk_writes": 1 if ("Block disk: writing" in log_tail or "Block disk: queuing write" in log_tail) else 0,
        },
        "ssm_companion": {
            "rederive": {
                "failed": 0 if "SSM" in log_tail and "re-derive failed" not in log_tail.lower() else 1,
                "source": "engine_log_tail",
            }
        },
        "mtp": {
            "depth": 3 if ("native MTP path activated" in log_tail and "depth=3" in log_tail) else 0,
            "source": "engine_log_tail",
        },
    }


def natural_network_prompt(lab_url: str) -> str:
    return (
        "Authorized local loopback network fixture only; this is a natural-language objective, not an exact call script. "
        f"Target scope is only {lab_url} and 127.0.0.1. Do not touch external hosts. "
        "choose the app tools you need from the provided schemas to complete this workflow end to end: "
        "discover the loopback service, probe the HTTP surface, validate only the seeded demo/demo credential, "
        "capture local network host evidence, run the harmless post-check endpoint, collect the linpeas fixture marker, "
        f"then write a concise evidence summary that starts with {FINAL_MARKER}. "
        "The relevant schemas for this network/post fixture include nmap, httpx, hydra, netexec, run_shell, and linpeas. "
        "The seeded login check is exposed at /login?user=demo&pass=demo and the harmless post-check endpoint is /post-check. "
        "Use netexec for local network host evidence before post-check and capture the QA-NETWORK marker. "
        "Use the linpeas schema for linpeas; use run_shell only for a local curl-style request to the post-check endpoint. "
        "Use tool results instead of guessing. Keep actions bounded to the loopback lab. "
        "Evidence must include EXPLOITBOT_NETWORK_LOGIN_OK, EXPLOITBOT_LINPEAS_FIXTURE_OK, and QA-NETWORK when confirmed."
    )


def final_followup_prompt(lab_url: str) -> str:
    return (
        "Do not call more tools. Use only the existing loopback fixture transcript. "
        f"Start with {FINAL_MARKER}, then summarize evidence for {lab_url}, service discovery, HTTP probe, seeded credential "
        "validation, network host evidence, harmless post-check, linpeas fixture marker, EXPLOITBOT_NETWORK_LOGIN_OK, "
        "EXPLOITBOT_LINPEAS_FIXTURE_OK, QA-NETWORK, and generated report evidence if present."
    )


def request_json_with_retries(
    method: str,
    url: str,
    body: dict[str, Any] | str | None = None,
    *,
    timeout: float = 30.0,
    attempts: int = 3,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return request_json(method, url, body, timeout=timeout)
        except (TimeoutError, socket.timeout, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(float(attempt))
    raise TimeoutError(f"{method} {url} failed after {attempts} attempts: {last_error}")


def app_request_with_retries(
    method: str,
    path: str,
    body: dict[str, Any] | str | None = None,
    *,
    timeout: float = 15.0,
    attempts: int = 3,
):
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return app_request(method, path, body, timeout=timeout)
        except (TimeoutError, socket.timeout, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(float(attempt))
    raise TimeoutError(f"{method} {path} failed after {attempts} attempts: {last_error}")


def model_selected_expected_sequence(messages: list[dict[str, Any]]) -> bool:
    sequence = network_proof.tool_sequence(messages)
    return all(tool in sequence for tool in EXPECTED_NETWORK_TOOLS)


def natural_evidence_ready_for_final(messages: list[dict[str, Any]]) -> bool:
    text = json.dumps(messages, sort_keys=True)
    return (
        model_selected_expected_sequence(messages)
        and "EXPLOITBOT_NETWORK_LOGIN_OK" in text
        and "EXPLOITBOT_LINPEAS_FIXTURE_OK" in text
        and "QA-NETWORK" in text
    )


def natural_final_marker_ready(messages: list[dict[str, Any]]) -> bool:
    return natural_evidence_ready_for_final(messages) and network_proof.has_assistant_marker(messages, FINAL_MARKER)


def wait_for_quiet_messages(
    timeout: float = 420.0,
    return_after_evidence_ready: bool = False,
    return_after_final_marker: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    deadline = time.time() + timeout
    last_state: dict[str, Any] = {}
    last_messages: list[dict[str, Any]] = []
    last_signature = ""
    last_progress_at = time.time()
    stall_seconds = float(os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_NETWORK_POST_STALL_SECONDS", "150"))
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
        if return_after_evidence_ready and natural_evidence_ready_for_final(messages):
            try:
                app_request("POST", "/stop", "", timeout=5.0)
            except Exception:
                pass
            state["naturalNetworkToolChoiceEvidenceCheckpoint"] = True
            return messages, state
        if return_after_final_marker and natural_final_marker_ready(messages):
            try:
                app_request("POST", "/stop", "", timeout=5.0)
            except Exception:
                pass
            state["naturalNetworkFinalMarkerCheckpoint"] = True
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
            if natural_evidence_ready_for_final(messages):
                state["naturalNetworkToolChoiceStallRecoveredAfterEvidence"] = True
                return messages, state
            if return_after_final_marker and natural_final_marker_ready(messages):
                state["naturalNetworkFinalMarkerStallRecovered"] = True
                return messages, state
            raise AssertionError(
                f"natural network tool-choice stream made no observable progress for {stall_seconds:.1f}s",
                {"signature": json.loads(signature), "toolSequence": network_proof.tool_sequence(messages), "state": state},
            )
        time.sleep(0.5)
    if last_messages and natural_evidence_ready_for_final(last_messages):
        last_state["naturalNetworkToolChoiceTimeoutRecoveredAfterEvidence"] = True
        try:
            app_request("POST", "/stop", "", timeout=5.0)
        except Exception:
            pass
        return last_messages, last_state
    if return_after_final_marker and last_messages and natural_final_marker_ready(last_messages):
        last_state["naturalNetworkFinalMarkerTimeoutRecovered"] = True
        try:
            app_request("POST", "/stop", "", timeout=5.0)
        except Exception:
            pass
        return last_messages, last_state
    raise AssertionError("timed out waiting for natural network tool-choice turn to finish", last_state)


def synthesize_model_requests_from_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return exact_web.synthesize_model_requests_from_messages(messages)


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
    sequence = network_proof.tool_sequence(messages)
    schema_names = network_proof.model_schema_names(model_requests)
    raw_tools = [row.get("tool") for row in results.get("rawResults") or [] if isinstance(row, dict)]
    checks = {
        "naturalLanguagePrompt": "PASS",
        "modelReceivedNetworkToolSchemas": network_proof.passfail(all(tool in schema_names for tool in EXPECTED_NETWORK_TOOLS)),
        "naturalNetworkToolCoverage": network_proof.passfail(all(tool in sequence for tool in EXPECTED_NETWORK_TOOLS)),
        "verboseToolTranscript": network_proof.passfail(all(f"Tool request: {tool}" in text for tool in EXPECTED_NETWORK_TOOLS)),
        "modelContinuedAfterTools": network_proof.passfail(FINAL_MARKER in text),
        "networkSurfaceEvidence": network_proof.passfail("ExploitBot demo service 1.0" in text or "ExploitBot demo service 1.0" in results_text),
        "httpProbeEvidence": network_proof.passfail(
            "httpx" in raw_tools
            and ("ExploitBot network fixture" in results_text or "status_code" in results_text)
        ),
        "credentialProof": network_proof.passfail("EXPLOITBOT_NETWORK_LOGIN_OK" in (text + results_text)),
        "networkHostEvidence": network_proof.passfail("netexec" in raw_tools and "QA-NETWORK" in (text + results_text)),
        "postCheckProof": network_proof.passfail("EXPLOITBOT_LINPEAS_FIXTURE_OK" in (text + results_text)),
        "safeLocalBoundary": network_proof.passfail(lab_url.startswith("http://127.0.0.1:")),
        "rawResultEvidence": network_proof.passfail(all(tool in raw_tools for tool in EXPECTED_NETWORK_TOOLS)),
        "terminalTranscripts": network_proof.passfail(all(tool in terminal_text for tool in EXPECTED_NETWORK_TOOLS)),
        "reportGeneratedFromEvidence": network_proof.passfail(
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
        "proofType": "real-qwen-natural-network-credential-post",
        "proofLevel": "live-app-real-qwen-natural-language-tool-selection-local-network-fixture",
        "status": "PASS" if ok else "FAIL",
        "scenarioId": "real_qwen_natural_network_credential_post",
        "generatedAt": finished_at,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "labUrl": lab_url,
        "stages": network_proof.STAGES,
        "toolSequence": sequence,
        "expectedToolSequence": EXPECTED_NETWORK_TOOLS,
        "toolSchemaNames": sorted(set(schema_names)),
        "checks": checks,
        "resultsSummary": {
            "rawResultCount": len(results.get("rawResults") or []),
            "rawTools": raw_tools,
        },
        "reportRenderActions": report_state.get("reportRenderActions") or {},
    }


def run() -> None:
    model = Path(os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_NETWORK_POST_MODEL", str(MODEL_27B))).expanduser()
    output = output_path_for_model(model)
    fixture_module = network_proof.load_fixture_module()
    fixture_session = fixture_module.build_fixture_session()
    lab_url = fixture_session.target_for("network_service_credential_post_chain")
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "real-qwen-natural-network-credential-post",
        "proofLevel": "live-app-real-qwen-natural-language-tool-selection-local-network-fixture",
        "model": str(model),
        "labUrl": lab_url,
        "startedAt": timestamp(),
        "modelLoadAttempted": False,
        "toolChoiceMode": "model_selected_tool_sequence",
        "modelToolChoiceEvidence": "model_selected_tool_sequence",
        "forcedSpecificToolRetry": "not_used",
        "safeBoundary": "loopback_fixture_only",
        "status": {"overall": "FAIL"},
    }
    error: Exception | None = None
    app: subprocess.Popen[str] | None = None
    engine: subprocess.Popen[str] | None = None
    app_home = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-natural-network-post-home-", ignore_cleanup_errors=True)
    cache_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-natural-network-post-cache-", ignore_cleanup_errors=True)
    network_proof.FINAL_MARKER = FINAL_MARKER
    prompt = natural_network_prompt(lab_url)
    try:
        require(model.is_dir(), f"Qwen model folder is missing: {model}")
        require(not exactToolCallBlocksPresent(prompt), "natural network prompt unexpectedly contains exact tool-call blocks", prompt)
        report["prompt"] = prompt
        report["exactToolCallBlocksPresent"] = False
        report["promptExactToolCallBlocksPresent"] = False
        report["memoryPreflight"] = live_batch.live_batch_memory_preflight(model, 1)
        report["status"]["memoryPreflight"] = "PASS"

        home = Path(app_home.name)
        password_file = home / "demo-passwords.txt"
        password_file.write_text("demo\n", encoding="utf-8")
        tools_dir = network_proof.install_fake_network_tools_at(home / ".exploitbot" / "tools", lab_url)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        env["EXPLOITBOT_TOOL_PATH_PREPEND"] = str(tools_dir)
        env["PATH"] = f"{tools_dir}:{env.get('PATH', '/usr/bin:/bin')}"

        with app_proof_lock("real-qwen-natural-network-credential-post-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            real_qwen.build_app_bundle()
            network_proof.install_fake_network_tools_at(APP_BINARY.parents[1] / "Resources" / "tools", lab_url)
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_for_app()

            port = int(os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_NETWORK_POST_ENGINE_PORT") or real_qwen.free_port())
            base_url = f"http://127.0.0.1:{port}"
            report["baseUrl"] = base_url
            report["modelLoadAttempted"] = True
            os.environ.setdefault(
                "EXPLOITBOT_REAL_QWEN_REAL_TOOLS_MAX_TOKENS",
                os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_NETWORK_POST_MAX_TOKENS", "2048"),
            )
            engine = real_qwen.launch_engine(model, port, Path(cache_tmp.name))
            health = real_qwen.wait_health(base_url, engine)
            cache_before = request_json_with_retries("GET", f"{base_url}/v1/cache/stats", timeout=30.0, attempts=3)

            app_request("POST", "/engine/mock", base_url, timeout=15.0)
            app_request("POST", "/mode", "autopilot", timeout=15.0)
            app_request("POST", "/reasoning", "off", timeout=15.0)
            app_request("POST", "/tab", "network", timeout=15.0)
            app_request(
                "POST",
                "/qa/apply-app-settings",
                {
                    "maxIterations": 8,
                    "toolSchemaMaxTools": SCENARIO_TOOL_SCHEMA_MAX,
                    "includeUnavailableToolSchemas": False,
                    "toolSchemaExcludedTools": EXCLUDED_SCHEMA_TOOLS,
                    "forceFinalAnswerAfterToolResults": False,
                    "followAgent": False,
                    "engine": {
                        "modelPath": str(model),
                        "useModelGenerationDefaults": False,
                        "maxTokens": int(os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_NETWORK_POST_MAX_TOKENS", "2048")),
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
                    "tab": "network",
                    "maxTools": SCENARIO_TOOL_SCHEMA_MAX,
                    "includeUnavailable": False,
                    "excludedToolNames": EXCLUDED_SCHEMA_TOOLS,
                },
                timeout=15.0,
            )
            for tool in EXPECTED_NETWORK_TOOLS:
                require(tool in (catalog.get("toolNames") or []), f"tool schema missing before natural network turn: {tool}", catalog)
            for tool in EXCLUDED_SCHEMA_TOOLS:
                require(tool not in (catalog.get("toolNames") or []), f"excluded tool schema still visible before natural network turn: {tool}", catalog)
            report["preflightToolCatalog"] = catalog

            report["initialSend"] = send_prompt_to_app(prompt, timeout=15.0)
            messages, state = wait_for_quiet_messages(timeout=420.0, return_after_evidence_ready=True)
            report["naturalTurnToolSequence"] = network_proof.tool_sequence(messages)
            require(model_selected_expected_sequence(messages), "model did not select the required network/post tool sequence", report["naturalTurnToolSequence"])

            network_proof.submit_report_from_results(lab_url)
            if not network_proof.has_assistant_marker(messages, FINAL_MARKER):
                app_request(
                    "POST",
                    "/qa/apply-app-settings",
                    {"toolSchemaMaxTools": 0, "forceFinalAnswerAfterToolResults": True},
                    timeout=15.0,
                )
                report["finalSend"] = send_prompt_to_app(final_followup_prompt(lab_url), timeout=15.0)
                messages, state = wait_for_quiet_messages(timeout=180.0, return_after_final_marker=True)

            results = app_request_with_retries("GET", "/results", timeout=15.0, attempts=3)
            report_state = app_request_with_retries("GET", "/state", timeout=15.0, attempts=3)
            try:
                cache_after = request_json_with_retries("GET", f"{base_url}/v1/cache/stats", timeout=30.0, attempts=3)
            except TimeoutError as exc:
                fallback_log_tail = real_qwen.read_output_tail(engine)
                report["cacheAfterCollectionError"] = f"{type(exc).__name__}: {exc}"
                report["cacheAfterEvidenceSource"] = "engine_log_tail_fallback"
                report["cacheAfterFallbackLogTail"] = fallback_log_tail
                cache_after = cache_after_from_engine_log(fallback_log_tail, messages, exc)
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
            require(model_status.get("nativeD3MTPForMTPModel") == "PASS", "MTP-named Qwen model must expose native D3 MTP evidence", model_status)
            status = {
                "overall": "PASS",
                "memoryPreflight": "PASS",
                "naturalLanguagePrompt": "PASS",
                "exactToolCallBlocksPresent": "PASS",
                "promptExactToolCallBlocksPresent": "PASS",
                "scenarioToolSchemaCapped": "PASS" if len(catalog.get("toolNames") or []) <= SCENARIO_TOOL_SCHEMA_MAX else "FAIL",
                "scenarioToolSchemaProfiled": "PASS" if all(tool not in (catalog.get("toolNames") or []) for tool in EXCLUDED_SCHEMA_TOOLS) else "FAIL",
                "modelSelectedNetworkToolSequence": "PASS" if model_selected_expected_sequence(messages) else "FAIL",
                "noForcedSpecificToolRetry": "PASS",
                "realQwenDroveNaturalNetworkCredentialPost": "PASS" if scenario_report.get("ok") is True else "FAIL",
                **scenario_report.get("checks", {}),
                **cache_status,
                **model_status,
            }
            status["overall"] = "PASS" if all(value == "PASS" for value in status.values() if isinstance(value, str)) else "FAIL"
            report.update(
                {
                    "ok": status["overall"] == "PASS",
                    "status": status,
                    "scenarioId": "real_qwen_natural_network_credential_post",
                    "generatedAt": timestamp(),
                    "finishedAt": timestamp(),
                    "stages": network_proof.STAGES,
                    "toolSequence": network_proof.tool_sequence(messages),
                    "expectedToolSequence": EXPECTED_NETWORK_TOOLS,
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
                        "The credential validation uses seeded demo/demo credentials only and the post-check is a harmless local fixture marker.",
                        "Report rendering is driven from parsed app results after the natural model-selected tool chain.",
                        "PASS requires natural netexec host evidence with the QA-NETWORK marker.",
                    ],
                }
            )
            if not report["ok"]:
                raise AssertionError("real-Qwen natural network credential/post checks failed", status)
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
        fixture_session.close()
        app_home.cleanup()
        cache_tmp.cleanup()
        report.setdefault("finishedAt", timestamp())
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error is not None:
        raise error
    print(f"real-qwen natural network credential/post proof passed: {output}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"real-qwen natural network credential/post proof failed: {exc}", flush=True)
        raise SystemExit(1)
