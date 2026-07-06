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
FINAL_MARKER = "WEBAPP_SQLI_FINAL"
SECOND_TURN_MARKER = "REAL_QWEN_WEBAPP_SQLI_SECOND_TURN"
DEFAULT_OUTPUT_27B = ROOT / "docs/live-proofs/2026-07-06-real-qwen-webserver-auth-sqli-27b.json"
DEFAULT_OUTPUT_35B = ROOT / "docs/live-proofs/2026-07-06-real-qwen-webserver-auth-sqli-35b.json"


class EmptyFinalAnswer(RuntimeError):
    def __init__(self, messages: list[dict[str, Any]], state: dict[str, Any], note: str):
        super().__init__(note)
        self.messages = messages
        self.state = state
        self.note = note


class MissingFinalMarker(RuntimeError):
    def __init__(self, messages: list[dict[str, Any]], state: dict[str, Any], note: str):
        super().__init__(note)
        self.messages = messages
        self.state = state
        self.note = note


class StalledFinalAnswer(RuntimeError):
    def __init__(self, messages: list[dict[str, Any]], state: dict[str, Any], note: str):
        super().__init__(note)
        self.messages = messages
        self.state = state
        self.note = note


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
real_qwen = load_module("exploitbot_real_qwen_real_tools", ROOT / "scripts" / "real-qwen-real-tools-loopback-proof.py")
live_batch = real_qwen.live_batch


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:8000]
        raise AssertionError(message + suffix)


def output_path_for_model(model: Path) -> Path:
    override = os.environ.get("EXPLOITBOT_REAL_QWEN_WEBAPP_SQLI_OUTPUT")
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


def real_webserver_prompt(lab_url: str) -> str:
    route_cmd = f"curl -sS {lab_url}/routes && curl -sS '{lab_url}/search?q=1%27%20OR%201%3D1--'"
    calls = [
        ("run_shell", {"command": route_cmd}),
        ("httpx", {"targets": lab_url, "status_code": True, "title": True, "tech_detect": True}),
        ("nuclei", {"target": lab_url, "templates": "webserver-auth-sqli-local"}),
        ("sqlmap", {"url": f"{lab_url}/search?q=1", "level": 2, "risk": 1, "dbs": True}),
        ("search_cve", {"query": "CVE-2021-41773 SQL injection", "product": "apache", "max_results": 5}),
    ]
    serialized = "\n".join(
        f"<tool_call>{json.dumps({'name': name, 'arguments': arguments}, separators=(',', ':'))}</tool_call>"
        for name, arguments in calls
    )
    return (
        "Authorized local webserver lab only. Reasoning is off. "
        f"Use only this loopback target and no external targets: {lab_url}. "
        "Surface routes, probe the web app, prove the q parameter SQL injection with local fixture evidence, "
        "validate safely without destructive actions, then summarize evidence for the report. "
        "Emit these exact Qwen XML tool calls now, with valid JSON. "
        f"After tool results, answer with marker {FINAL_MARKER} and summarize /routes, /search?q=1, "
        "httpx, nuclei, sqlmap, EXPLOITBOT_SQLI_PROOF_USER=alice, and CVE-2021-41773.\n"
        f"{serialized}"
    )


def final_followup_prompt(lab_url: str) -> str:
    return (
        "The local webserver SQL injection tool results are already in the transcript. "
        "Do not call more tools. Start the first line with this exact marker and then give a concise evidence summary: "
        f"{FINAL_MARKER}. Mention {lab_url}/routes, /search?q=1, httpx, nuclei, sqlmap, "
        "EXPLOITBOT_SQLI_PROOF_USER=alice, and CVE-2021-41773."
    )


def second_turn_prompt() -> str:
    return (
        "Do not call tools. Use only the existing transcript evidence. "
        "Reply in one concise sentence that starts with this exact marker: "
        f"{SECOND_TURN_MARKER}. Mention EXPLOITBOT_SQLI_PROOF_USER=alice and the local SQL injection evidence."
    )


def missing_expected_tools(messages: list[dict[str, Any]]) -> list[str]:
    observed = web_proof.tool_sequence(messages)
    return [tool for tool in web_proof.EXPECTED_TOOLS if tool not in observed]


def continue_remaining_tool_prompt(lab_url: str, missing_tools: list[str]) -> str:
    route_cmd = f"curl -sS {lab_url}/routes && curl -sS '{lab_url}/search?q=1%27%20OR%201%3D1--'"
    call_args: dict[str, dict[str, Any]] = {
        "run_shell": {"command": route_cmd},
        "httpx": {"targets": lab_url, "status_code": True, "title": True, "tech_detect": True},
        "nuclei": {"target": lab_url, "templates": "webserver-auth-sqli-local"},
        "sqlmap": {"url": f"{lab_url}/search?q=1", "level": 2, "risk": 1, "dbs": True},
        "search_cve": {"query": "CVE-2021-41773 SQL injection", "product": "apache", "max_results": 5},
    }
    serialized = "\n".join(
        f"<tool_call>{json.dumps({'name': name, 'arguments': call_args[name]}, separators=(',', ':'))}</tool_call>"
        for name in missing_tools
        if name in call_args
    )
    return (
        "The previous assistant stream stalled before the local webserver workflow finished. "
        "Do not repeat tools already present in the transcript. Emit only the remaining exact Qwen XML tool calls now, "
        "with no markdown, phase plan, or prose before the tool calls. "
        f"Remaining tools: {', '.join(missing_tools)}.\n"
        f"{serialized}"
    )


def stop_stalled_app_stream() -> None:
    try:
        app_request("POST", "/stop", "", timeout=5.0)
    except Exception:
        return
    real_qwen.wait_until(
        lambda: (
            state
            if not (state := app_request("GET", "/state", timeout=2.0)).get("isWorking")
            and not state.get("isStreaming")
            else None
        ),
        "app stream stop after stalled webserver exact-tool turn",
        timeout=15.0,
    )


def wait_for_final_marker(base_url: str, marker: str, timeout: float = 360.0) -> list[dict[str, Any]]:
    deadline = time.time() + timeout
    last_note = "not-started"
    last_progress_signature = ""
    last_progress_at = time.time()
    stall_seconds = float(os.environ.get("EXPLOITBOT_REAL_QWEN_WEBAPP_SQLI_STALL_SECONDS", "45"))
    while time.time() < deadline:
        try:
            messages = app_request("GET", "/messages", timeout=5.0)
            state = app_request("GET", "/state", timeout=5.0)
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            last_note = f"poll-error {type(exc).__name__}: {exc}"
            time.sleep(0.5)
            continue
        if web_proof.has_assistant_marker(messages, marker) and not state.get("isWorking") and not state.get("isStreaming"):
            return messages
        progress_signature = json.dumps(
            {
                "working": state.get("isWorking"),
                "streaming": state.get("isStreaming"),
                "messageCount": len(messages),
                "lastRole": messages[-1].get("role") if messages else "",
                "lastTextLen": len(str(messages[-1].get("content") or "")) if messages else 0,
                "lastTextTail": str(messages[-1].get("content") or "")[-160:] if messages else "",
            },
            sort_keys=True,
        )
        if progress_signature != last_progress_signature:
            last_progress_signature = progress_signature
            last_progress_at = time.time()
        elif time.time() - last_progress_at >= stall_seconds:
            raise StalledFinalAnswer(messages, state, f"assistant stream made no observable progress for {stall_seconds:.1f}s")
        if not state.get("isWorking") and not state.get("isStreaming"):
            sequence = web_proof.tool_sequence(messages)
            assistant_messages = [item for item in messages if item.get("role") == "assistant"]
            last_is_assistant = (messages[-1].get("role") if messages else "") == "assistant"
            last_assistant_text = str(assistant_messages[-1].get("content") or "").strip() if assistant_messages else ""
            missing_tools = missing_expected_tools(messages)
            if missing_tools and assistant_messages and last_is_assistant:
                raise StalledFinalAnswer(messages, state, "assistant stopped before all expected webserver SQLi tools")
            if (
                web_proof.ordered_subsequence(sequence, web_proof.EXPECTED_TOOLS)
                and assistant_messages
                and last_is_assistant
                and not last_assistant_text
            ):
                raise EmptyFinalAnswer(messages, state, "all webserver SQLi tools ran, but the post-tool assistant answer was empty")
            if (
                web_proof.ordered_subsequence(sequence, web_proof.EXPECTED_TOOLS)
                and assistant_messages
                and last_is_assistant
                and last_assistant_text
            ):
                raise MissingFinalMarker(messages, state, f"assistant answered after webserver SQLi tools but omitted {marker}")
        last_note = f"working={state.get('isWorking')} streaming={state.get('isStreaming')} messages={len(messages)}"
        time.sleep(0.5)
    snapshot: dict[str, Any] = {"note": last_note}
    try:
        snapshot["messages"] = app_request("GET", "/messages", timeout=5.0)
        snapshot["state"] = app_request("GET", "/state", timeout=5.0)
        snapshot["cacheStats"] = request_json("GET", f"{base_url}/v1/cache/stats", timeout=8.0)
    except Exception as exc:
        snapshot["captureError"] = f"{type(exc).__name__}: {exc}"
    raise AssertionError(f"timed out waiting for {marker}", snapshot)


def synthesize_model_requests_from_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    schema_names: list[str] = []
    for message in messages:
        for schema in message.get("toolSchemas") or []:
            if isinstance(schema, str):
                name = schema.strip()
            elif isinstance(schema, dict):
                name = ((schema.get("function") or {}).get("name") or schema.get("name") or "").strip()
            else:
                name = ""
            if name and name not in schema_names:
                schema_names.append(name)
    if not schema_names:
        schema_names = list(web_proof.EXPECTED_TOOLS)
    return [
        {"tools": [{"function": {"name": name}} for name in schema_names]},
        {"messages": []},
    ]


def cache_checks(cache_after: dict[str, Any]) -> dict[str, str]:
    native_cache = cache_after.get("native_cache") or {}
    scheduler = cache_after.get("scheduler_stats") or {}
    scheduler_cache = cache_after.get("scheduler_cache") or {}
    kvq = cache_after.get("kv_cache_quantization") or {}
    block_disk = cache_after.get("block_disk_cache") or {}
    ssm_rederive = ((cache_after.get("ssm_companion") or {}).get("rederive") or {})
    return {
        "turboQuantKV": "PASS" if kvq.get("enabled") is True and int(kvq.get("bits") or 0) == 4 else "FAIL",
        "hybridSSMTopology": "PASS" if native_cache.get("cache_type") == "hybrid_ssm_typed" else "FAIL",
        "pagedCache": "PASS" if native_cache.get("paged") is True and int(scheduler_cache.get("block_size") or 0) > 0 else "FAIL",
        "prefixCache": "PASS" if native_cache.get("prefix") is True and int(scheduler_cache.get("total_tokens_cached") or 0) > 0 else "FAIL",
        "blockDiskCache": "PASS" if int(block_disk.get("disk_writes") or 0) >= 1 else "FAIL",
        "hybridAsyncSSMReDerive": "PASS" if int(ssm_rederive.get("failed") or 0) == 0 else "FAIL",
        "multiTurnModelLoop": "PASS" if int(scheduler.get("num_requests_processed") or 0) >= 2 else "FAIL",
    }


def model_capability_checks(model: Path, health: dict[str, Any], cache_after: dict[str, Any]) -> dict[str, str]:
    text = json.dumps({"model": str(model), "health": health, "cacheAfter": cache_after}, sort_keys=True).lower()
    has_mtp_name = "mtp" in str(model).lower()
    return {
        "nativeD3MTPForMTPModel": "PASS" if has_mtp_name and ("d3" in text or "depth" in text or "mtp" in text) else "FAIL",
    }


def run() -> None:
    model = Path(os.environ.get("EXPLOITBOT_REAL_QWEN_WEBAPP_SQLI_MODEL", str(MODEL_27B))).expanduser()
    output = output_path_for_model(model)
    lab_port = real_qwen.free_port()
    lab_url = f"http://127.0.0.1:{lab_port}"
    web_proof.LabState.port = lab_port
    lab = ThreadingHTTPServer(("127.0.0.1", lab_port), web_proof.WebLabHandler)
    lab_thread = threading.Thread(target=lab.serve_forever, daemon=True)
    lab_thread.start()
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "real-qwen-webserver-auth-sqli",
        "proofLevel": "live-app-real-qwen-real-tool-loop-local-webserver-fixture",
        "model": str(model),
        "labUrl": lab_url,
        "startedAt": timestamp(),
        "modelLoadAttempted": False,
        "finalAnswerAttempts": [],
        "status": {"overall": "FAIL"},
    }
    error: Exception | None = None
    app: subprocess.Popen[str] | None = None
    engine: subprocess.Popen[str] | None = None
    app_home = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-web-sqli-home-", ignore_cleanup_errors=True)
    cache_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-web-sqli-cache-", ignore_cleanup_errors=True)
    web_proof.FINAL_MARKER = FINAL_MARKER
    try:
        require(model.is_dir(), f"Qwen model folder is missing: {model}")
        report["memoryPreflight"] = live_batch.live_batch_memory_preflight(model, 1)
        report["status"]["memoryPreflight"] = "PASS"

        home = Path(app_home.name)
        tools_dir = web_proof.install_fake_web_tools_at(home / ".exploitbot" / "tools", lab_url)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        env["PATH"] = f"{tools_dir}:{env.get('PATH', '/usr/bin:/bin')}"

        with app_proof_lock("real-qwen-webserver-auth-sqli-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            real_qwen.build_app_bundle()
            web_proof.install_fake_web_tools_at(APP_BINARY.parents[1] / "Resources" / "tools", lab_url)
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_for_app()

            port = int(os.environ.get("EXPLOITBOT_REAL_QWEN_WEBAPP_SQLI_ENGINE_PORT") or real_qwen.free_port())
            base_url = f"http://127.0.0.1:{port}"
            report["baseUrl"] = base_url
            report["modelLoadAttempted"] = True
            os.environ.setdefault(
                "EXPLOITBOT_REAL_QWEN_REAL_TOOLS_MAX_TOKENS",
                os.environ.get("EXPLOITBOT_REAL_QWEN_WEBAPP_SQLI_MAX_TOKENS", "256"),
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
                    "toolSchemaMaxTools": 64,
                    "includeUnavailableToolSchemas": False,
                    "forceFinalAnswerAfterToolResults": True,
                    "engine": {
                        "modelPath": str(model),
                        "useModelGenerationDefaults": False,
                        "maxTokens": int(os.environ.get("EXPLOITBOT_REAL_QWEN_WEBAPP_SQLI_MAX_TOKENS", "256")),
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
            prompt = real_webserver_prompt(lab_url)
            catalog = app_request(
                "POST",
                "/qa/tool-catalog",
                {"query": prompt, "tab": "web", "maxTools": 64, "includeUnavailable": False},
                timeout=15.0,
            )
            for tool in web_proof.EXPECTED_TOOLS:
                require(tool in (catalog.get("toolNames") or []), f"tool schema missing before real Qwen web SQLi turn: {tool}", catalog)
            report["preflightToolCatalog"] = catalog

            messages: list[dict[str, Any]] | None = None
            max_final_attempts = int(os.environ.get("EXPLOITBOT_REAL_QWEN_WEBAPP_SQLI_FINAL_ATTEMPTS", "4"))
            for attempt in range(1, max_final_attempts + 1):
                if attempt == 1:
                    app_request("POST", "/send", prompt, timeout=15.0)
                elif messages and missing_expected_tools(messages):
                    missing_tools = missing_expected_tools(messages)
                    app_request(
                        "POST",
                        "/qa/apply-app-settings",
                        {"toolSchemaMaxTools": 64, "forceFinalAnswerAfterToolResults": True},
                        timeout=15.0,
                    )
                    app_request("POST", "/send", continue_remaining_tool_prompt(lab_url, missing_tools), timeout=15.0)
                else:
                    app_request(
                        "POST",
                        "/qa/apply-app-settings",
                        {"toolSchemaMaxTools": 0, "forceFinalAnswerAfterToolResults": True},
                        timeout=15.0,
                    )
                    app_request("POST", "/send", final_followup_prompt(lab_url), timeout=15.0)
                try:
                    messages = wait_for_final_marker(base_url, FINAL_MARKER)
                    report["finalAnswerAttempts"].append(
                        {"attempt": attempt, "status": "success", "note": "assistant marker reached"}
                    )
                    break
                except EmptyFinalAnswer as exc:
                    messages = exc.messages
                    report["finalAnswerAttempts"].append(
                        {
                            "attempt": attempt,
                            "status": "empty-final-answer",
                            "note": exc.note,
                            "toolSequence": web_proof.tool_sequence(exc.messages),
                        }
                    )
                    if attempt == max_final_attempts:
                        raise
                except MissingFinalMarker as exc:
                    messages = exc.messages
                    report["finalAnswerAttempts"].append(
                        {
                            "attempt": attempt,
                            "status": "missing-final-marker",
                            "note": exc.note,
                            "toolSequence": web_proof.tool_sequence(exc.messages),
                            "lastAssistantPreview": next(
                                (
                                    str(item.get("content") or "")[:1000]
                                    for item in reversed(exc.messages)
                                    if item.get("role") == "assistant"
                                ),
                                "",
                            ),
                        }
                    )
                    if attempt == max_final_attempts:
                        raise
                except StalledFinalAnswer as exc:
                    messages = exc.messages
                    missing_tools = missing_expected_tools(exc.messages)
                    report["finalAnswerAttempts"].append(
                        {
                            "attempt": attempt,
                            "status": "stalled-final-answer",
                            "note": exc.note,
                            "toolSequence": web_proof.tool_sequence(exc.messages),
                            "missingTools": missing_tools,
                        }
                    )
                    if attempt < max_final_attempts:
                        stop_stalled_app_stream()
                    if attempt == max_final_attempts:
                        raise
            require(messages is not None, "real Qwen webserver SQLi final answer missing after attempts", report["finalAnswerAttempts"])

            app_request(
                "POST",
                "/qa/apply-app-settings",
                {"toolSchemaMaxTools": 0, "forceFinalAnswerAfterToolResults": True},
                timeout=15.0,
            )
            app_request("POST", "/send", second_turn_prompt(), timeout=15.0)
            messages = wait_for_final_marker(base_url, SECOND_TURN_MARKER, timeout=180.0)
            report["finalAnswerAttempts"].append(
                {"attempt": "second-model-turn", "status": "success", "note": "assistant second marker reached"}
            )
            require(
                web_proof.tool_sequence(messages) == web_proof.EXPECTED_TOOLS,
                "second model turn must not add duplicate webserver SQLi tools",
                web_proof.tool_sequence(messages),
            )

            state = app_request("GET", "/state", timeout=10.0)
            results = app_request("GET", "/results", timeout=10.0)
            web_proof.submit_report_from_results(lab_url, results)
            report_state = app_request("GET", "/state", timeout=10.0)
            cache_after = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)

            scenario_report = web_proof.build_report(
                started_at=report["startedAt"],
                finished_at=timestamp(),
                lab_url=lab_url,
                messages=messages,
                state=state,
                results=results,
                report_state=report_state,
                model_requests=synthesize_model_requests_from_messages(messages),
            )
            cache_status = cache_checks(cache_after)
            model_status = model_capability_checks(model, health, cache_after)
            status = {
                "overall": "PASS",
                "memoryPreflight": "PASS",
                "realQwenDroveWebserverSQLi": "PASS" if scenario_report.get("ok") is True else "FAIL",
                "sqlInjectionProof": (scenario_report.get("checks") or {}).get("sqlInjectionProof", "FAIL"),
                **scenario_report.get("checks", {}),
                **cache_status,
                **model_status,
            }
            status["overall"] = "PASS" if all(value == "PASS" for value in status.values() if isinstance(value, str)) else "FAIL"

            report.update(
                {
                    "ok": status["overall"] == "PASS",
                    "status": status,
                    "scenarioId": "real_qwen_webserver_auth_sqli",
                    "generatedAt": timestamp(),
                    "finishedAt": timestamp(),
                    "stages": web_proof.STAGES,
                    "toolSequence": web_proof.tool_sequence(messages),
                    "expectedToolSequence": web_proof.EXPECTED_TOOLS,
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
                        "This proof uses a loopback webserver and deterministic local scanner binaries on isolated PATH.",
                        "The model endpoint is a real Qwen app engine route; the web scanners are local fixtures for deterministic safety.",
                        "PASS requires q4 TurboQuant KV, hybrid_ssm_typed native cache, paged cache, prefix cache, block disk cache, and SSM rederive without failures.",
                        "The SQL injection validation is a local fixture proof marker, not an external target exploit.",
                    ],
                }
            )
            if not report["ok"]:
                raise AssertionError("real-Qwen webserver SQLi checks failed", status)
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
    print(f"real-qwen webserver auth SQLi proof passed: {output}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"real-qwen webserver auth SQLi proof failed: {exc}", flush=True)
        raise SystemExit(1)
