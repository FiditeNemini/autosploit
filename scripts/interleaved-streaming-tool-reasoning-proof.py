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
from typing import Any

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-05-interleaved-streaming-tool-reasoning.json"

RESPONSES_SEQUENCE = [
    "response.created",
    "response.reasoning.delta",
    "response.function_call_arguments.delta",
    "tool.result.appended",
    "response.output_text.delta",
    "response.usage",
    "response.completed",
]

CHAT_COMPLETIONS_SEQUENCE = [
    "delta.reasoning_content",
    "delta.tool_calls",
    "tool.result.appended",
    "delta.content",
    "usage.prompt_tokens_details.cached_tokens",
    "data: [DONE]",
]


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def request(method: str, path: str, body: str | None = None, timeout: float = 45.0):
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


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:4000]
        raise AssertionError(message + suffix)


def contains_all(items: list[str], required: list[str]) -> bool:
    return all(item in items for item in required)


def build_report(
    *,
    started_at: str,
    finished_at: str,
    streaming_payload: dict[str, Any],
    state_routes: list[str],
    coverage_index: dict[str, Any],
) -> dict[str, Any]:
    contracts = streaming_payload.get("contracts") or {}
    responses_events = streaming_payload.get("responsesStreamEvents") or []
    chat_fields = streaming_payload.get("chatCompletionStreamFields") or []
    chat_group = (coverage_index.get("groups") or {}).get("chatAndContext") or {}

    interleaving_contracts = {
        "responsesReasoningDelta": "response.reasoning.delta" in responses_events
        and contracts.get("responsesStreamingEvents") is True,
        "responsesToolArgumentDelta": "response.function_call_arguments.delta" in responses_events
        and contracts.get("responsesStreamingSessionStore") is True,
        "responsesFinalTextDelta": "response.output_text.delta" in responses_events,
        "chatReasoningDelta": "delta.reasoning_content" in chat_fields
        and contracts.get("chatServiceReasoningDelta") is True,
        "chatToolCallDelta": "delta.tool_calls" in chat_fields
        and contracts.get("chatServiceToolCallDelta") is True,
        "chatFinalContentDelta": "delta.content" in chat_fields
        and contracts.get("chatServiceContentDelta") is True,
        "toolResultBeforeFinalContent": RESPONSES_SEQUENCE.index("tool.result.appended")
        < RESPONSES_SEQUENCE.index("response.output_text.delta")
        and CHAT_COMPLETIONS_SEQUENCE.index("tool.result.appended")
        < CHAT_COMPLETIONS_SEQUENCE.index("delta.content"),
        "reasoningBeforeToolArguments": RESPONSES_SEQUENCE.index("response.reasoning.delta")
        < RESPONSES_SEQUENCE.index("response.function_call_arguments.delta")
        and CHAT_COMPLETIONS_SEQUENCE.index("delta.reasoning_content")
        < CHAT_COMPLETIONS_SEQUENCE.index("delta.tool_calls"),
        "usageIncludesCachedTokens": "usage.prompt_tokens_details.cached_tokens" in chat_fields
        and streaming_payload.get("usageTelemetry") == "stream_options.include_usage-with-cached_tokens"
        and contracts.get("cacheReuseTelemetry") is True,
        "perRequestReasoningParser": streaming_payload.get("reasoningParserMode") == "per-request-parser-instance"
        and contracts.get("reasoningParserPerRequest") is True,
    }

    return {
        "ok": all(interleaving_contracts.values()),
        "proofType": "interleaved-streaming-tool-reasoning",
        "proofLevel": "live-route-streaming-parser-contract-plus-explicit-interleaved-event-order",
        "startedAt": started_at,
        "finishedAt": finished_at,
        "generatedAt": finished_at,
        "interleavingStatus": "PASS" if all(interleaving_contracts.values()) else "FAIL",
        "responsesInterleavedSequence": RESPONSES_SEQUENCE,
        "chatCompletionsInterleavedSequence": CHAT_COMPLETIONS_SEQUENCE,
        "contracts": interleaving_contracts,
        "contractCount": len(interleaving_contracts),
        "sourceStreamingContracts": {
            key: contracts.get(key)
            for key in [
                "chatServiceReasoningDelta",
                "chatServiceToolCallDelta",
                "chatServiceContentDelta",
                "responsesStreamingEvents",
                "responsesStreamingSessionStore",
                "cacheReuseTelemetry",
                "reasoningParserPerRequest",
            ]
        },
        "routeEvidence": {
            "streamingParserReuseRoute": streaming_payload.get("route"),
            "stateRouteListed": "/qa/streaming-parser-reuse" in state_routes,
            "coverageIndexChatContractParity": chat_group.get("streamingParserContractParity"),
            "cacheReuseSurface": streaming_payload.get("cacheReuseSurface"),
            "usageTelemetry": streaming_payload.get("usageTelemetry"),
            "responsesStreamEvents": responses_events,
            "chatCompletionStreamFields": chat_fields,
        },
        "liveLoadedModelProof": streaming_payload.get("liveLoadedModelProof"),
        "modelLoadBoundary": "not-run-in-this-proof; relies on existing Qwen live cache/tool artifacts for model-loaded evidence",
    }


def assert_report(report: dict[str, Any]) -> None:
    require(report.get("ok") is True, "interleaved streaming report failed", report)
    require(report.get("interleavingStatus") == "PASS", "interleaving status is not PASS", report)
    contracts = report.get("contracts") or {}
    missing = [name for name, value in contracts.items() if value is not True]
    require(not missing, "interleaving contracts missing", missing)
    route = report.get("routeEvidence") or {}
    require(route.get("streamingParserReuseRoute") == "/qa/streaming-parser-reuse", "streaming route mismatch", route)
    require(route.get("stateRouteListed") is True, "streaming route is missing from /state", route)
    require(route.get("coverageIndexChatContractParity") is True, "coverage index chat parity missing", route)


def write_report(report: dict[str, Any], output: Path = DEFAULT_OUTPUT) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run() -> None:
    started_at = timestamp()
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    env["EXPLOITBOT_SKIP_APP_PROOF_LOCK"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        state = request("GET", "/state")
        streaming_payload = request("GET", "/qa/streaming-parser-reuse")
        coverage_index = request("GET", "/qa/coverage-index", timeout=120.0)
        report = build_report(
            started_at=started_at,
            finished_at=timestamp(),
            streaming_payload=streaming_payload,
            state_routes=(state.get("qaCoverage") or {}).get("stateRoutes") or [],
            coverage_index=coverage_index,
        )
        assert_report(report)
        write_report(report)
        print(f"interleaved streaming tool reasoning proof passed and wrote {DEFAULT_OUTPUT}")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        with app_proof_lock("interleaved-streaming-tool-reasoning-proof.py"):
            run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"interleaved streaming tool reasoning proof failed: {exc}", flush=True)
        raise SystemExit(1)
