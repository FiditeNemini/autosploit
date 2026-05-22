#!/usr/bin/env python3
"""Prove reasoning and tool-call parser output is API-shaped."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "ExploitBotEngine"
sys.path.insert(0, str(ENGINE))

from vmlx_engine import server  # noqa: E402
from vmlx_engine.api.models import (  # noqa: E402
    AssistantMessage,
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ToolDefinition,
)
from vmlx_engine.reasoning import get_parser  # noqa: E402


def prove() -> dict:
    old_enabled = server._enable_auto_tool_choice
    old_tool_parser = server._tool_call_parser
    old_reasoning_parser = server._reasoning_parser
    old_reasoning_name = server._reasoning_parser_name
    old_engine = server._engine
    try:
        server._enable_auto_tool_choice = True
        server._tool_call_parser = "qwen"
        server._reasoning_parser_name = "qwen3"
        server._reasoning_parser = get_parser("qwen3")()
        server._engine = None

        request = ChatCompletionRequest(
            model="mock-qwen-jang",
            messages=[{"role": "user", "content": "run id"}],
            tools=[
                ToolDefinition(
                    function={
                        "name": "run_shell",
                        "parameters": {
                            "type": "object",
                            "properties": {"command": {"type": "string"}},
                        },
                    }
                )
            ],
        )
        raw_output = (
            "<think>Need the current user before escalating.</think>"
            "Ready.\n"
            '<tool_call>{"name":"run_shell","arguments":{"command":"id"}}</tool_call>'
        )

        reasoning, content_for_parsing = server._reasoning_parser.extract_reasoning(raw_output)
        cleaned, tool_calls = server._parse_tool_calls_with_parser(content_for_parsing, request)
        response = ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    message=AssistantMessage(
                        content=cleaned,
                        reasoning=reasoning,
                        tool_calls=tool_calls,
                    ),
                    finish_reason="tool_calls",
                )
            ],
        )
        dumped = response.model_dump(exclude_none=True)
        message = dumped["choices"][0]["message"]
        if message.get("tool_calls"):
            message["tool_calls"][0]["id"] = "generated-call-id"
        function = message["tool_calls"][0]["function"]
        ok = (
            message.get("content") == "Ready."
            and message.get("reasoning_content") == "Need the current user before escalating."
            and "reasoning" not in message
            and "<think>" not in message.get("content", "")
            and "<tool_call>" not in message.get("content", "")
            and function.get("name") == "run_shell"
            and function.get("arguments") == '{"command": "id"}'
            and dumped["choices"][0].get("finish_reason") == "tool_calls"
        )
        return {
            "ok": ok,
            "configured_parsers": {
                "reasoning": server._reasoning_parser_name,
                "tool_call": server._tool_call_parser,
                "auto_tool_choice": server._enable_auto_tool_choice,
            },
            "message": message,
            "finish_reason": dumped["choices"][0].get("finish_reason"),
        }
    finally:
        server._enable_auto_tool_choice = old_enabled
        server._tool_call_parser = old_tool_parser
        server._reasoning_parser = old_reasoning_parser
        server._reasoning_parser_name = old_reasoning_name
        server._engine = old_engine


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = prove()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
