#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import importlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = ROOT / "ExploitBotEngine"
sys.path.insert(0, str(ENGINE_ROOT))


class SchedulerConfig:
    enable_prefix_cache = True
    cache_memory_percent = 0.35
    use_paged_cache = True
    paged_cache_block_size = 128
    kv_cache_quantization = "turboquant-q4"
    kv_cache_group_size = 64
    enable_disk_cache = True
    disk_cache_dir = "/tmp/exploitbot-proof/prompt-l2"
    disk_cache_max_gb = 24.0
    enable_block_disk_cache = True
    block_disk_cache_dir = "/tmp/exploitbot-proof/block-l2"
    block_disk_cache_max_gb = 48.0
    ssm_state_cache_size = 32
    ssm_state_cache_max_mb = 1024


def require(condition: bool, message: str, payload: Any = None) -> None:
    if not condition:
        suffix = "" if payload is None else f": {json.dumps(payload, indent=2, sort_keys=True)}"
        raise AssertionError(f"{message}{suffix}")


def assert_metadata(metadata: dict[str, Any]) -> None:
    require(metadata["model"]["family"] == "qwen3_next", "missing Qwen model-family autodetect", metadata)
    require(metadata["model"]["cache_type"] == "mamba", "missing hybrid cache-family metadata", metadata)
    require(metadata["parsers"]["reasoning"] == "qwen3", "missing reasoning parser metadata", metadata)
    require(metadata["parsers"]["tool_call"] == "qwen", "missing tool parser metadata", metadata)
    require(metadata["parsers"]["auto_tool_choice"] is True, "missing tool-choice metadata", metadata)
    require(metadata["generation"]["temperature"] == 0.2, "missing generation default", metadata)
    require(
        metadata["generation"]["chat_template_kwargs"] == {"enable_thinking": True},
        "missing template generation defaults",
        metadata,
    )
    require(metadata["sources"]["generation"]["temperature"] == "generation_config", "missing generation provenance", metadata)
    require(metadata["sources"]["parsers"]["reasoning"] == "model_registry", "missing parser provenance", metadata)

    cache = metadata["cache"]
    require(cache["prefix_cache"]["enabled"] is True, "prefix cache must be enabled", cache)
    require(cache["paged_cache"]["enabled"] is True, "paged cache must be enabled", cache)
    require(cache["disk_cache"]["prompt_l2"]["enabled"] is True, "prompt L2 must be enabled", cache)
    require(cache["disk_cache"]["block_l2"]["enabled"] is True, "block L2 must be enabled", cache)
    require(cache["kv_cache_quantization"]["mode"] == "turboquant-q4", "TurboQuant Q4 metadata missing", cache)
    require(cache["ssm_companion"]["disk_l2_enabled"] is True, "SSM companion L2 metadata missing", cache)

    topology = cache["topology"]
    require(topology["name"] == "hybrid_ssm_attention", "wrong topology", topology)
    for component in (
        "kv_cache",
        "prefix_cache",
        "prompt_l2",
        "paged_cache",
        "block_l2",
        "kv_quantization",
        "ssm_companion",
        "ssm_l2",
    ):
        require(component in topology["expected_components"], f"missing topology component {component}", topology)

    responses = cache.get("responses")
    require(isinstance(responses, dict), "missing cache-response inference metadata", cache)
    require(responses.get("method") == "prefix-cache-l2-turboquant", "wrong cache-response method", responses)
    require(responses.get("prefix_cache_required") is True, "prefix cache requirement not surfaced", responses)
    require(responses.get("new_context_preserves_engine_session") is True, "new context cache preservation not surfaced", responses)


def run() -> None:
    server = importlib.import_module("vmlx_engine.server")

    saved = {
        "_engine": server._engine,
        "_standby_state": server._standby_state,
        "_cli_args": server._cli_args,
        "_model_name": server._model_name,
        "_model_path": server._model_path,
        "_served_model_name": server._served_model_name,
        "_model_type": server._model_type,
        "_reasoning_parser_name": server._reasoning_parser_name,
        "_reasoning_parser": server._reasoning_parser,
        "_tool_call_parser": server._tool_call_parser,
        "_enable_auto_tool_choice": server._enable_auto_tool_choice,
        "_default_temperature": server._default_temperature,
        "_default_top_p": server._default_top_p,
        "_default_top_k": server._default_top_k,
        "_default_min_p": server._default_min_p,
        "_default_repetition_penalty": server._default_repetition_penalty,
        "_default_stop": server._default_stop,
        "_default_max_tokens": server._default_max_tokens,
        "_default_enable_thinking": server._default_enable_thinking,
        "_default_chat_template_kwargs": server._default_chat_template_kwargs,
        "_custom_chat_template": server._custom_chat_template,
        "_model_load_error": server._model_load_error,
        "_max_prompt_tokens": server._max_prompt_tokens,
        "_jang_metadata": server._jang_metadata,
        "_effective_config_sources": server._effective_config_sources,
    }

    with tempfile.TemporaryDirectory() as tmp:
        model_dir = Path(tmp)
        (model_dir / "config.json").write_text(json.dumps({"model_type": "qwen3_next"}), encoding="utf-8")

        try:
            server._engine = None
            server._standby_state = None
            server._cli_args = {"scheduler_config": SchedulerConfig()}
            server._model_name = "Qwen3.5-Hybrid-JANGTQ"
            server._model_path = str(model_dir)
            server._served_model_name = "exploitbot-local"
            server._model_type = "text"
            server._reasoning_parser_name = "qwen3"
            server._reasoning_parser = None
            server._tool_call_parser = "qwen"
            server._enable_auto_tool_choice = True
            server._default_temperature = 0.2
            server._default_top_p = 0.88
            server._default_top_k = 40
            server._default_min_p = 0.02
            server._default_repetition_penalty = 1.05
            server._default_stop = ["<|im_end|>"]
            server._default_max_tokens = 8192
            server._default_enable_thinking = True
            server._default_chat_template_kwargs = {"enable_thinking": True}
            server._custom_chat_template = "{{ messages }}"
            server._model_load_error = None
            server._max_prompt_tokens = 0
            server._jang_metadata = None
            server._effective_config_sources = {
                "generation": {"temperature": "generation_config", "top_k": "cli"},
                "parsers": {"reasoning": "model_registry", "tool_call": "model_registry"},
            }

            health = asyncio.run(server.health())
            models = asyncio.run(server.list_models())

            require(health["status"] == "no_model", "health must report no_model", health)
            require(health["model_loaded"] is False, "health must not claim a loaded model", health)
            assert_metadata(health["effective_config"])

            require(len(models.data) == 2, "served and source model names should both be listed", models.model_dump())
            for item in models.data:
                require(item.metadata == health["effective_config"], "models metadata diverges from health", item.model_dump())
        finally:
            for name, value in saved.items():
                setattr(server, name, value)

    print("engine-no-model-metadata proof passed")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"engine-no-model-metadata proof failed: {exc}", flush=True)
        raise SystemExit(1)
