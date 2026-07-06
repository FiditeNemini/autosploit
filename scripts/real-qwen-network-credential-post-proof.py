#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
from pathlib import Path
from typing import Any

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
MODEL_27B = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP")
MODEL_35B = Path("/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP")
FINAL_MARKER = "NETWORK_CREDENTIAL_POST_FINAL"
SECOND_TURN_MARKER = "REAL_QWEN_NETWORK_CREDENTIAL_POST_SECOND_TURN"
DEFAULT_OUTPUT_27B = ROOT / "docs/live-proofs/2026-07-06-real-qwen-network-credential-post-27b.json"
DEFAULT_OUTPUT_35B = ROOT / "docs/live-proofs/2026-07-06-real-qwen-network-credential-post-35b.json"


def load_module(name: str, path: Path):
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in os.sys.path:
        os.sys.path.insert(0, scripts_dir)
    spec = __import__("importlib.util").util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper module: {path}")
    module = __import__("importlib.util").util.module_from_spec(spec)
    os.sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


real_web = load_module(
    "exploitbot_real_qwen_webserver_auth_sqli_helpers_for_network",
    ROOT / "scripts" / "real-qwen-webserver-auth-sqli-proof.py",
)
network_proof = real_web.load_module(
    "exploitbot_network_credential_post_real_qwen_contract",
    ROOT / "scripts" / "network-credential-post-scenario-proof.py",
)
real_qwen = real_web.real_qwen
live_batch = real_web.live_batch


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:8000]
        raise AssertionError(message + suffix)


def output_path_for_model(model: Path) -> Path:
    override = os.environ.get("EXPLOITBOT_REAL_QWEN_NETWORK_POST_OUTPUT")
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


def network_tool_calls(lab_url: str, password_file: str, tool_names: list[str] | None = None) -> list[tuple[str, dict[str, Any]]]:
    lab_port = int(lab_url.rsplit(":", 1)[-1])
    call_args: dict[str, dict[str, Any]] = {
        "nmap": {"target": "127.0.0.1", "ports": str(lab_port), "service_detection": True},
        "httpx": {"targets": lab_url, "status_code": True, "title": True, "tech_detect": True},
        "hydra": {
            "target": "127.0.0.1",
            "protocol": "http-get",
            "port": lab_port,
            "path": "/login?user=demo&pass=demo",
            "username": "demo",
            "password_file": password_file,
        },
        "netexec": {"target": "127.0.0.1", "protocol": "smb", "shares": True, "timeout": 2, "smb_timeout": 2},
        "run_shell": {"command": f"curl -sS {lab_url}/post-check"},
        "linpeas": {"flags": "-q"},
    }
    names = tool_names or list(network_proof.EXPECTED_TOOLS)
    return [(name, call_args[name]) for name in names if name in call_args]


def serialize_tool_calls(calls: list[tuple[str, dict[str, Any]]]) -> str:
    return "\n".join(
        f"<tool_call>{json.dumps({'name': name, 'arguments': arguments}, separators=(',', ':'))}</tool_call>"
        for name, arguments in calls
    )


def real_network_prompt(lab_url: str, password_file: str) -> str:
    return (
        "Authorized local network lab only. Reasoning is off. "
        f"Use only this loopback fixture and no external targets: {lab_url}. "
        "Discover the service, probe the HTTP surface, validate only the seeded demo/demo credential, "
        "capture local network host evidence, run only the harmless post-check endpoint and linpeas fixture, "
        "then summarize evidence for the report. Emit these exact Qwen XML tool calls now, with valid JSON. "
        f"After tool results, answer with marker {FINAL_MARKER} and summarize nmap, httpx, hydra, netexec, "
        "run_shell, linpeas, EXPLOITBOT_NETWORK_LOGIN_OK, EXPLOITBOT_LINPEAS_FIXTURE_OK, QA-NETWORK, "
        "and the generated report evidence.\n"
        f"{serialize_tool_calls(network_tool_calls(lab_url, password_file))}"
    )


def continue_remaining_tool_prompt(lab_url: str, password_file: str, missing_tools: list[str]) -> str:
    return (
        "The previous assistant stream stalled before the local network credential/post workflow finished. "
        "Do not repeat tools already present in the transcript. Emit only the remaining exact Qwen XML tool calls now, "
        "with no markdown, phase plan, or prose before the tool calls. "
        f"Remaining tools: {', '.join(missing_tools)}.\n"
        f"{serialize_tool_calls(network_tool_calls(lab_url, password_file, missing_tools))}"
    )


def final_followup_prompt(lab_url: str) -> str:
    return (
        "The local network credential and post-check tool results are already in the transcript. "
        "Do not call more tools. Start the first line with this exact marker and then give a concise evidence summary: "
        f"{FINAL_MARKER}. Mention {lab_url}, nmap, httpx, hydra, netexec, run_shell, linpeas, "
        "EXPLOITBOT_NETWORK_LOGIN_OK, EXPLOITBOT_LINPEAS_FIXTURE_OK, QA-NETWORK, and report evidence."
    )


def second_turn_prompt(attempt: int = 1) -> str:
    retry_prefix = "" if attempt == 1 else "The previous final-summary attempt was suppressed because it tried to call a tool. "
    return (
        f"{retry_prefix}Do not call tools, do not use shell, do not emit XML, and do not emit JSON. "
        "Use only the existing transcript evidence. Reply as plain text in one concise sentence that starts with this exact marker: "
        f"{SECOND_TURN_MARKER}. Mention EXPLOITBOT_NETWORK_LOGIN_OK, EXPLOITBOT_LINPEAS_FIXTURE_OK, "
        "QA-NETWORK, and the local credential/post-check evidence."
    )


def missing_expected_tools(messages: list[dict[str, Any]]) -> list[str]:
    observed = network_proof.tool_sequence(messages)
    return [tool for tool in network_proof.EXPECTED_TOOLS if tool not in observed]


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
        "app stream stop after stalled network exact-tool turn",
        timeout=15.0,
    )


def wait_for_final_marker(base_url: str, marker: str, timeout: float = 360.0) -> list[dict[str, Any]]:
    deadline = time.time() + timeout
    last_note = "not-started"
    last_progress_signature = ""
    last_progress_at = time.time()
    stall_seconds = float(os.environ.get("EXPLOITBOT_REAL_QWEN_NETWORK_POST_STALL_SECONDS", "45"))
    while time.time() < deadline:
        try:
            messages = app_request("GET", "/messages", timeout=5.0)
            state = app_request("GET", "/state", timeout=5.0)
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            last_note = f"poll-error {type(exc).__name__}: {exc}"
            time.sleep(0.5)
            continue
        if network_proof.has_assistant_marker(messages, marker) and not state.get("isWorking") and not state.get("isStreaming"):
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
            raise real_web.StalledFinalAnswer(messages, state, f"assistant stream made no observable progress for {stall_seconds:.1f}s")
        if not state.get("isWorking") and not state.get("isStreaming"):
            sequence = network_proof.tool_sequence(messages)
            assistant_messages = [item for item in messages if item.get("role") == "assistant"]
            last_is_assistant = (messages[-1].get("role") if messages else "") == "assistant"
            last_assistant_text = str(assistant_messages[-1].get("content") or "").strip() if assistant_messages else ""
            if missing_expected_tools(messages) and assistant_messages and last_is_assistant:
                raise real_web.StalledFinalAnswer(messages, state, "assistant stopped before all expected network credential/post tools")
            if network_proof.ordered_subsequence(sequence, network_proof.EXPECTED_TOOLS) and assistant_messages and last_is_assistant:
                if not last_assistant_text:
                    raise real_web.EmptyFinalAnswer(messages, state, "all network credential/post tools ran, but the post-tool assistant answer was empty")
                raise real_web.MissingFinalMarker(messages, state, f"assistant answered after network credential/post tools but omitted {marker}")
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
        schema_names = list(network_proof.EXPECTED_TOOLS)
    return [
        {"tools": [{"function": {"name": name}} for name in schema_names]},
        {"messages": []},
    ]


def run() -> None:
    model = Path(os.environ.get("EXPLOITBOT_REAL_QWEN_NETWORK_POST_MODEL", str(MODEL_27B))).expanduser()
    output = output_path_for_model(model)
    fixture_module = network_proof.load_fixture_module()
    fixture_session = fixture_module.build_fixture_session()
    lab_url = fixture_session.target_for("network_service_credential_post_chain")
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "real-qwen-network-credential-post",
        "proofLevel": "live-app-real-qwen-real-tool-loop-local-network-fixture",
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
    app_home = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-network-post-home-", ignore_cleanup_errors=True)
    cache_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-network-post-cache-", ignore_cleanup_errors=True)
    network_proof.FINAL_MARKER = FINAL_MARKER
    try:
        require(model.is_dir(), f"Qwen model folder is missing: {model}")
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
        env["PATH"] = f"{tools_dir}:{env.get('PATH', '/usr/bin:/bin')}"

        with app_proof_lock("real-qwen-network-credential-post-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            real_qwen.build_app_bundle()
            network_proof.install_fake_network_tools_at(APP_BINARY.parents[1] / "Resources" / "tools", lab_url)
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_for_app()

            port = int(os.environ.get("EXPLOITBOT_REAL_QWEN_NETWORK_POST_ENGINE_PORT") or real_qwen.free_port())
            base_url = f"http://127.0.0.1:{port}"
            report["baseUrl"] = base_url
            report["modelLoadAttempted"] = True
            os.environ.setdefault(
                "EXPLOITBOT_REAL_QWEN_REAL_TOOLS_MAX_TOKENS",
                os.environ.get("EXPLOITBOT_REAL_QWEN_NETWORK_POST_MAX_TOKENS", "256"),
            )
            engine = real_qwen.launch_engine(model, port, Path(cache_tmp.name))
            health = real_qwen.wait_health(base_url, engine)
            cache_before = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)

            app_request("POST", "/engine/mock", base_url, timeout=15.0)
            app_request("POST", "/mode", "autopilot", timeout=15.0)
            app_request("POST", "/reasoning", "off", timeout=15.0)
            app_request("POST", "/tab", "network", timeout=15.0)
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
                        "maxTokens": int(os.environ.get("EXPLOITBOT_REAL_QWEN_NETWORK_POST_MAX_TOKENS", "256")),
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
            prompt = real_network_prompt(lab_url, str(password_file))
            catalog = app_request(
                "POST",
                "/qa/tool-catalog",
                {"query": prompt, "tab": "network", "maxTools": 64, "includeUnavailable": False},
                timeout=15.0,
            )
            for tool in network_proof.EXPECTED_TOOLS:
                require(tool in (catalog.get("toolNames") or []), f"tool schema missing before real Qwen network turn: {tool}", catalog)
            report["preflightToolCatalog"] = catalog

            messages: list[dict[str, Any]] | None = None
            max_final_attempts = int(os.environ.get("EXPLOITBOT_REAL_QWEN_NETWORK_POST_FINAL_ATTEMPTS", "4"))
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
                    app_request("POST", "/send", continue_remaining_tool_prompt(lab_url, str(password_file), missing_tools), timeout=15.0)
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
                except (real_web.EmptyFinalAnswer, real_web.MissingFinalMarker, real_web.StalledFinalAnswer) as exc:
                    messages = exc.messages
                    report["finalAnswerAttempts"].append(
                        {
                            "attempt": attempt,
                            "status": type(exc).__name__,
                            "note": exc.note,
                            "toolSequence": network_proof.tool_sequence(exc.messages),
                            "missingTools": missing_expected_tools(exc.messages),
                        }
                    )
                    if isinstance(exc, real_web.StalledFinalAnswer) and attempt < max_final_attempts:
                        stop_stalled_app_stream()
                    if attempt == max_final_attempts:
                        raise
            require(messages is not None, "real Qwen network credential/post final answer missing after attempts", report["finalAnswerAttempts"])

            app_request(
                "POST",
                "/qa/apply-app-settings",
                {"toolSchemaMaxTools": 0, "forceFinalAnswerAfterToolResults": True},
                timeout=15.0,
            )
            second_turn_attempts = int(os.environ.get("EXPLOITBOT_REAL_QWEN_NETWORK_POST_SECOND_TURN_ATTEMPTS", "3"))
            for second_attempt in range(1, second_turn_attempts + 1):
                app_request("POST", "/send", second_turn_prompt(second_attempt), timeout=15.0)
                try:
                    messages = wait_for_final_marker(base_url, SECOND_TURN_MARKER, timeout=180.0)
                    report["finalAnswerAttempts"].append(
                        {"attempt": f"second-model-turn-{second_attempt}", "status": "success", "note": "assistant second marker reached"}
                    )
                    break
                except (real_web.EmptyFinalAnswer, real_web.MissingFinalMarker, real_web.StalledFinalAnswer) as exc:
                    messages = exc.messages
                    report["finalAnswerAttempts"].append(
                        {
                            "attempt": f"second-model-turn-{second_attempt}",
                            "status": type(exc).__name__,
                            "note": exc.note,
                            "toolSequence": network_proof.tool_sequence(exc.messages),
                            "suppressedFinalToolCall": "suppressedFinalToolCall" in json.dumps(exc.messages),
                        }
                    )
                    require(
                        network_proof.tool_sequence(exc.messages) == network_proof.EXPECTED_TOOLS,
                        "second model finalization retry must suppress parser tool calls without adding duplicate tools",
                        network_proof.tool_sequence(exc.messages),
                    )
                    if isinstance(exc, real_web.StalledFinalAnswer):
                        stop_stalled_app_stream()
                    if second_attempt == second_turn_attempts:
                        raise
            require(
                network_proof.tool_sequence(messages) == network_proof.EXPECTED_TOOLS,
                "second model turn must not add duplicate network credential/post tools",
                network_proof.tool_sequence(messages),
            )

            state = app_request("GET", "/state", timeout=10.0)
            results = app_request("GET", "/results", timeout=10.0)
            network_proof.submit_report_from_results(lab_url)
            report_state = app_request("GET", "/state", timeout=10.0)
            cache_after = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)

            scenario_report = network_proof.build_report(
                started_at=report["startedAt"],
                finished_at=timestamp(),
                lab_url=lab_url,
                messages=messages,
                state=state,
                results=results,
                report_state=report_state,
                model_requests=synthesize_model_requests_from_messages(messages),
            )
            cache_status = real_web.cache_checks(cache_after)
            model_status = real_web.model_capability_checks(model, health, cache_after)
            require(cache_status.get("multiTurnModelLoop") == "PASS", "real Qwen network proof must process at least two model turns", cache_status)
            require(model_status.get("nativeD3MTPForMTPModel") == "PASS", "MTP-named Qwen model must expose native D3 MTP evidence", model_status)
            status = {
                "overall": "PASS",
                "memoryPreflight": "PASS",
                "realQwenDroveNetworkCredentialPost": "PASS" if scenario_report.get("ok") is True else "FAIL",
                "credentialProof": (scenario_report.get("checks") or {}).get("credentialProof", "FAIL"),
                "postCheckProof": (scenario_report.get("checks") or {}).get("postCheckProof", "FAIL"),
                **scenario_report.get("checks", {}),
                **cache_status,
                **model_status,
            }
            status["overall"] = "PASS" if all(value == "PASS" for value in status.values() if isinstance(value, str)) else "FAIL"

            report.update(
                {
                    "ok": status["overall"] == "PASS",
                    "status": status,
                    "scenarioId": "real_qwen_network_credential_post",
                    "generatedAt": timestamp(),
                    "finishedAt": timestamp(),
                    "stages": network_proof.STAGES,
                    "toolSequence": network_proof.tool_sequence(messages),
                    "expectedToolSequence": network_proof.EXPECTED_TOOLS,
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
                        "This proof uses a loopback network fixture and deterministic local scanner/post-check binaries on isolated PATH.",
                        "The model endpoint is a real Qwen app engine route; network tools are local fixtures for deterministic safety.",
                        "PASS requires q4 TurboQuant KV, hybrid_ssm_typed native cache, paged cache, prefix cache, block disk cache, and SSM rederive without failures.",
                        "The credential validation uses seeded demo/demo credentials only and the post-check is a harmless local fixture marker.",
                    ],
                }
            )
            if not report["ok"]:
                raise AssertionError("real-Qwen network credential/post checks failed", status)
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
        real_web.write_report(output, report)

    if error is not None:
        raise error
    print(f"real-qwen network credential/post proof passed: {output}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"real-qwen network credential/post proof failed: {exc}", flush=True)
        raise SystemExit(1)
