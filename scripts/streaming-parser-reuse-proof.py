#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"

EXPECTED_ENDPOINTS = [
    "/v1/chat/completions",
    "/v1/responses",
]

EXPECTED_RESPONSES_EVENTS = [
    "response.created",
    "response.output_text.delta",
    "response.reasoning.delta",
    "response.function_call_arguments.delta",
    "response.usage",
    "response.completed",
]

EXPECTED_STREAM_FIELDS = [
    "data: [DONE]",
    "choices",
    "delta.content",
    "delta.reasoning_content",
    "delta.tool_calls",
    "usage.prompt_tokens_details.cached_tokens",
]

EXPECTED_TOOL_PARSERS = [
    "qwen_tool_parser.py",
    "minimax_tool_parser.py",
    "auto_tool_parser.py",
]

EXPECTED_ENGINE_TEST_FILES = [
    "ExploitBotEngine/testsuite/test_responses_session_store.py",
    "ExploitBotEngine/testsuite/test_tool_parser_api.py",
    "scripts/prove-parser-api.py",
]

EXPECTED_ENGINE_TEST_COMMANDS = [
    "cd ExploitBotEngine && PYTHONPATH=. .venv/bin/python -m pytest -q testsuite/test_responses_session_store.py testsuite/test_tool_parser_api.py",
    "ExploitBotEngine/.venv/bin/python scripts/prove-parser-api.py",
]

EXPECTED_CONTRACTS = {
    "chatCompletionsStreaming",
    "chatServiceUsageMetrics",
    "chatServiceContentDelta",
    "chatServiceReasoningDelta",
    "chatServiceToolCallDelta",
    "responsesEndpoint",
    "responsesPreviousResponseReuse",
    "responsesStreamingEvents",
    "responsesUsageCachedTokens",
    "qwenStreamingToolParser",
    "minimaxStreamingToolParser",
    "autoToolParserFallback",
    "reasoningParserPerRequest",
    "toolChoiceRequiredErrors",
    "cacheReuseTelemetry",
    "responsesSessionStoreEngineTests",
    "parserAPIShapeProof",
}


def request(method: str, path: str, body: str | None = None, timeout: float = 15.0):
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def wait_for_app(timeout: float = 15.0) -> None:
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


def assert_source_files(payload: dict) -> None:
    source_files = payload.get("sourceFiles") or []
    if payload.get("sourceFileParity") is not True:
        raise AssertionError(f"streaming parser source-file parity mismatch: {payload}")
    missing = [name for name in source_files if not (ROOT / name).is_file()]
    if missing:
        raise AssertionError(f"streaming parser source files missing on disk: {missing}")


def assert_payload(payload: dict) -> None:
    if payload.get("ok") is not True:
        raise AssertionError(f"streaming parser reuse route failed: {payload}")
    if payload.get("proofLevel") != "app-source-and-engine-test-backed":
        raise AssertionError(f"streaming parser proof level mismatch: {payload}")
    if payload.get("supportedFamilies") != ["qwen", "minimax"]:
        raise AssertionError(f"streaming parser supported family mismatch: {payload}")
    if payload.get("streamingEndpoints") != EXPECTED_ENDPOINTS:
        raise AssertionError(f"streaming parser endpoint mismatch: {payload}")
    if payload.get("responsesStreamEvents") != EXPECTED_RESPONSES_EVENTS:
        raise AssertionError(f"Responses stream event list mismatch: {payload}")
    if payload.get("chatCompletionStreamFields") != EXPECTED_STREAM_FIELDS:
        raise AssertionError(f"chat stream field list mismatch: {payload}")
    if payload.get("toolParserFiles") != EXPECTED_TOOL_PARSERS:
        raise AssertionError(f"tool parser file list mismatch: {payload}")
    if payload.get("cacheReuseSurface") != "previous_response_id-plus-prefix-cache-l2-turboquant":
        raise AssertionError(f"cache reuse surface mismatch: {payload}")
    if payload.get("liveLoadedModelProof") != "not-run-in-this-gate":
        raise AssertionError(f"streaming parser live proof label mismatch: {payload}")
    if payload.get("engineTestFiles") != EXPECTED_ENGINE_TEST_FILES:
        raise AssertionError(f"streaming parser engine test file list mismatch: {payload}")
    if payload.get("engineTestFileParity") is not True:
        raise AssertionError(f"streaming parser engine test file parity mismatch: {payload}")
    if payload.get("engineTestCommands") != EXPECTED_ENGINE_TEST_COMMANDS:
        raise AssertionError(f"streaming parser engine test command list mismatch: {payload}")
    if payload.get("engineTestCommandCount") != len(EXPECTED_ENGINE_TEST_COMMANDS):
        raise AssertionError(f"streaming parser engine test command count mismatch: {payload}")
    if payload.get("responsesStoreSessionMode") != "store-response-session-and-resolve-previous-response-id":
        raise AssertionError(f"Responses session store mode mismatch: {payload}")
    if payload.get("usageTelemetry") != "stream_options.include_usage-with-cached_tokens":
        raise AssertionError(f"usage telemetry mismatch: {payload}")

    contracts = payload.get("contracts") or {}
    missing_contracts = sorted(name for name in EXPECTED_CONTRACTS if contracts.get(name) is not True)
    if missing_contracts:
        raise AssertionError(f"streaming parser contracts missing {missing_contracts}: {payload}")
    if payload.get("contractCount") != len(EXPECTED_CONTRACTS):
        raise AssertionError(f"streaming parser contract count mismatch: {payload}")
    if payload.get("contractParity") is not True:
        raise AssertionError(f"streaming parser contract parity mismatch: {payload}")
    if payload.get("proofFileParity") is not True:
        raise AssertionError(f"streaming parser proof-file parity mismatch: {payload}")
    assert_source_files(payload)


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        state = request("GET", "/state")
        payload = request("GET", "/qa/streaming-parser-reuse")
        chat = request("GET", "/qa/chat-coverage")
        runtime = request("GET", "/qa/runtime-coverage")
        deep = request("GET", "/qa/deep-runtime-flow-coverage")
        index = request("GET", "/qa/coverage-index")

        assert_payload(payload)

        routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/streaming-parser-reuse" not in routes:
            raise AssertionError(f"state routes missing streaming parser reuse route: {routes}")
        if "/qa/streaming-parser-reuse" not in (chat.get("routes") or []):
            raise AssertionError(f"chat coverage missing streaming parser route: {chat}")
        if "/qa/streaming-parser-reuse" not in (runtime.get("routes") or []):
            raise AssertionError(f"runtime coverage missing streaming parser route: {runtime}")
        if "/qa/streaming-parser-reuse" not in (deep.get("routes") or []):
            raise AssertionError(f"deep runtime coverage missing streaming parser route: {deep}")

        chat_group = (index.get("groups") or {}).get("chatAndContext") or {}
        runtime_group = (index.get("groups") or {}).get("runtimeAndCache") or {}
        if "/qa/streaming-parser-reuse" not in (chat_group.get("endpoints") or []):
            raise AssertionError(f"coverage index chat group missing streaming route: {chat_group}")
        if "/qa/streaming-parser-reuse" not in (runtime_group.get("endpoints") or []):
            raise AssertionError(f"coverage index runtime group missing streaming route: {runtime_group}")
        if chat_group.get("streamingParserContractParity") is not True:
            raise AssertionError(f"coverage index chat group missing streaming contract parity: {chat_group}")
        if runtime_group.get("streamingParserContractParity") is not True:
            raise AssertionError(f"coverage index runtime group missing streaming contract parity: {runtime_group}")

        print("streaming-parser-reuse proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"streaming-parser-reuse proof failed: {exc}", flush=True)
        raise SystemExit(1)
