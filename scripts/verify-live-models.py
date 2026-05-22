#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = ROOT / "ExploitBotEngine"
LAUNCH_PY = ENGINE_DIR / "launch.py"


class VerificationError(RuntimeError):
    def __init__(self, message: str, reports: dict[str, Any] | None = None):
        super().__init__(message)
        self.reports = reports or {}


def _read_output_tail(stream: Any, max_lines: int = 80) -> str:
    if stream is None:
        return ""
    try:
        lines = stream.readlines() if hasattr(stream, "readlines") else list(stream)
    except Exception as exc:
        return f"<unable to read engine output: {exc}>"
    return "".join(lines[-max_lines:])


def _engine_python() -> str:
    override = os.environ.get("EXPLOITBOT_ENGINE_PYTHON")
    if override:
        return override
    venv_python = ENGINE_DIR / ".venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _load_launch_module():
    spec = importlib.util.spec_from_file_location("exploitbot_launch", LAUNCH_PY)
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    sys.path.insert(0, str(ENGINE_DIR))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
    return module


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        return {"__error": f"invalid json: {exc}"}


def _family_for(path: Path, config: dict[str, Any]) -> str:
    haystack = f"{path} {config.get('model_type', '')} {config.get('architectures', '')}".lower()
    if "qwen" in haystack:
        return "qwen"
    if "minimax" in haystack:
        return "minimax"
    return "unknown" if not config else "unsupported"


def inspect_model_folder(path: str | Path, expected_family: str | None = None) -> dict[str, Any]:
    path = Path(path).expanduser().resolve()
    config = _read_json(path / "config.json")
    jang = _read_json(path / "jang_config.json")
    jangtq = _read_json(path / "jangtq_config.json")
    generation = _read_json(path / "generation_config.json")
    family = _family_for(path, config)
    supported = family in {"qwen", "minimax"}
    expected_ok = expected_family in (None, family) or (expected_family == "unsupported" and not supported)

    return {
        "path": str(path),
        "exists": path.exists(),
        "family": family,
        "expected_family": expected_family,
        "expected_ok": expected_ok,
        "supported": supported,
        "model_type": config.get("model_type"),
        "has_config": bool(config) and "__error" not in config,
        "has_jang_config": bool(jang) and "__error" not in jang,
        "has_jangtq_config": bool(jangtq) and "__error" not in jangtq,
        "has_generation_config": bool(generation) and "__error" not in generation,
        "has_tokenizer_config": (path / "tokenizer_config.json").exists(),
        "generation_keys": sorted(k for k in generation.keys() if not k.startswith("__")),
        "jang_capabilities": jang.get("capabilities", {}) if isinstance(jang.get("capabilities"), dict) else {},
        "errors": [v["__error"] for v in (config, jang, jangtq, generation) if "__error" in v],
    }


def build_launch_args(path: str | Path, port: int, cache_root: str | Path | None = None) -> list[str]:
    launch = _load_launch_module()
    path = Path(path).expanduser().resolve()
    defaults = launch.load_model_folder_defaults(str(path))
    cache_root_path = Path(cache_root).expanduser().resolve() if cache_root else None
    return launch.build_args(
        str(path),
        port=port,
        model_defaults=defaults,
        reasoning_parser="auto",
        tool_call_parser="auto",
        kv_cache_quantization="turboquant-q4",
        kv_cache_group_size=64,
        enable_prefix_cache=True,
        enable_disk_cache=True,
        disk_cache_dir=(cache_root_path / "prompt") if cache_root_path else None,
        disk_cache_max_gb=10.0,
        cache_memory_percent=0.30,
        use_paged_cache=True,
        paged_cache_block_size=64,
        enable_block_disk_cache=True,
        block_disk_cache_dir=(cache_root_path / "block") if cache_root_path else None,
        block_disk_cache_max_gb=10.0,
    )


def build_live_engine_command(
    path: str | Path,
    *,
    port: int,
    cache_root: str | Path,
    enable_prompt_disk: bool = True,
) -> list[str]:
    path = Path(path).expanduser().resolve()
    cache_root = Path(cache_root)
    cmd = [
        _engine_python(),
        str(LAUNCH_PY),
        "--model",
        str(path),
        "--port",
        str(port),
        "--reasoning-parser",
        "auto",
        "--tool-call-parser",
        "auto",
        "--kv-cache-quantization",
        "turboquant-q4",
        "--enable-prefix-cache",
        "true",
        "--enable-disk-cache",
        "true" if enable_prompt_disk else "false",
    ]
    if enable_prompt_disk:
        cmd.extend([
            "--disk-cache-dir",
            str(cache_root / "prompt"),
        ])
    cmd.extend([
        "--use-paged-cache",
        "true",
        "--enable-block-disk-cache",
        "true",
        "--block-disk-cache-dir",
        str(cache_root / "block"),
        "--max-tokens",
        "64",
        "--verbose",
    ])
    return cmd


def _find_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _request_json(method: str, url: str, body: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    api_key = os.environ.get("VMLX_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _wait_health(
    base_url: str,
    timeout: float,
    proc: subprocess.Popen[str] | None = None,
    report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            if report is not None:
                report["engine_exit_code"] = proc.returncode
                report["engine_log_tail"] = _read_output_tail(proc.stdout)
            raise RuntimeError(f"engine exited before health check passed: exit {proc.returncode}")
        try:
            health = _request_json("GET", f"{base_url}/health", timeout=5.0)
            if health.get("status") == "healthy":
                return health
            last_error = RuntimeError(json.dumps(health, sort_keys=True)[:1000])
        except Exception as exc:
            last_error = exc
        time.sleep(1.0)
    raise RuntimeError(f"engine did not become healthy: {last_error}")


def _assert_runtime_metadata(report: dict[str, Any], health: dict[str, Any], models: dict[str, Any], cache: dict[str, Any]) -> None:
    effective = health.get("effective_config") or {}
    effective_text = json.dumps(effective, sort_keys=True).lower()
    cache_text = json.dumps(cache, sort_keys=True).lower()
    model_text = json.dumps(models, sort_keys=True).lower()

    required = {
        "effective_config": bool(effective),
        "models_metadata": "metadata" in model_text,
        "prefix_cache": "prefix" in effective_text or "prefix" in cache_text,
        "prompt_l2_disk": "disk" in effective_text or "disk_cache" in cache,
        "paged_cache": "paged" in effective_text or "paged" in cache_text,
        "block_l2_disk": "block" in effective_text or "block_disk_cache" in cache,
        "turboquant": "turbo" in effective_text or "turbo" in cache_text or health.get("kv_cache_quantization") is not None,
    }
    report["runtime_checks"] = required
    missing = [name for name, ok in required.items() if not ok]
    if missing:
        raise RuntimeError(f"missing runtime metadata checks: {', '.join(missing)}")


def _assert_completion(completion: dict[str, Any]) -> None:
    usage = completion.get("usage") or {}
    choices = completion.get("choices") or []
    token_count = usage.get("completion_tokens") or 0
    has_content = False
    for choice in choices:
        message = choice.get("message") or {}
        if message.get("content") or message.get("reasoning_content") or message.get("tool_calls"):
            has_content = True
            break
    if not has_content:
        if token_count > 0:
            raise RuntimeError("empty assistant message: token usage reported without content/reasoning/tool_calls")
        raise RuntimeError("empty completion: model returned no tokens/content")


def _int_at(data: dict[str, Any], path: tuple[str, ...]) -> int:
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return 0
        value = value.get(key)
    return int(value or 0) if isinstance(value, (int, float)) else 0


def _cached_tokens_from_completion(completion: dict[str, Any]) -> int:
    usage = completion.get("usage") or {}
    details = usage.get("prompt_tokens_details") or {}
    return _int_at({"details": details}, ("details", "cached_tokens"))


def _assert_repeat_cache_behavior(
    report: dict[str, Any],
    first_cache: dict[str, Any],
    second_cache: dict[str, Any],
    second_completion: dict[str, Any],
) -> None:
    cached_tokens = _cached_tokens_from_completion(second_completion)
    counters = {
        "scheduler_hits_delta": _int_at(second_cache, ("scheduler_cache", "hits")) - _int_at(first_cache, ("scheduler_cache", "hits")),
        "scheduler_cache_hits_delta": _int_at(second_cache, ("scheduler_cache", "cache_hits")) - _int_at(first_cache, ("scheduler_cache", "cache_hits")),
        "scheduler_disk_hits_delta": _int_at(second_cache, ("scheduler_cache", "disk_hits")) - _int_at(first_cache, ("scheduler_cache", "disk_hits")),
        "scheduler_tokens_saved_delta": _int_at(second_cache, ("scheduler_cache", "tokens_saved")) - _int_at(first_cache, ("scheduler_cache", "tokens_saved")),
        "prompt_l2_hits_delta": _int_at(second_cache, ("disk_cache", "hits")) - _int_at(first_cache, ("disk_cache", "hits")),
        "block_l2_hits_delta": _int_at(second_cache, ("block_disk_cache", "disk_hits")) - _int_at(first_cache, ("block_disk_cache", "disk_hits")),
        "ssm_l2_hits_delta": _int_at(second_cache, ("ssm_companion", "disk", "hits")) - _int_at(first_cache, ("ssm_companion", "disk", "hits")),
    }
    checks = {
        "cached_usage": cached_tokens > 0,
        "cache_hit_counter": any(value > 0 for value in counters.values()),
    }
    report["repeat_cache_checks"] = {
        **checks,
        "cached_tokens": cached_tokens,
        **counters,
    }
    if not checks["cached_usage"] and not checks["cache_hit_counter"]:
        raise RuntimeError("repeat cache check failed: no cached usage or cache-hit counter increment")


def _assert_restart_replay_cache_behavior(
    report: dict[str, Any],
    first_run_cache: dict[str, Any],
    replay_run_cache: dict[str, Any],
    replay_completion: dict[str, Any],
    *,
    require_block_l2: bool = False,
) -> None:
    cached_tokens = _cached_tokens_from_completion(replay_completion)
    counters = {
        "scheduler_disk_hits_delta": _int_at(replay_run_cache, ("scheduler_cache", "disk_hits")) - _int_at(first_run_cache, ("scheduler_cache", "disk_hits")),
        "scheduler_tokens_saved_delta": _int_at(replay_run_cache, ("scheduler_cache", "tokens_saved")) - _int_at(first_run_cache, ("scheduler_cache", "tokens_saved")),
        "prompt_l2_hits_delta": _int_at(replay_run_cache, ("disk_cache", "hits")) - _int_at(first_run_cache, ("disk_cache", "hits")),
        "block_l2_hits_delta": _int_at(replay_run_cache, ("block_disk_cache", "disk_hits")) - _int_at(first_run_cache, ("block_disk_cache", "disk_hits")),
        "ssm_l2_hits_delta": _int_at(replay_run_cache, ("ssm_companion", "disk", "hits")) - _int_at(first_run_cache, ("ssm_companion", "disk", "hits")),
    }
    checks = {
        "cached_usage": cached_tokens > 0,
        "l2_disk_hit": any(value > 0 for value in counters.values()),
    }
    report["restart_replay_cache_checks"] = {
        **checks,
        "cached_tokens": cached_tokens,
        **counters,
    }
    if not checks["cached_usage"] and not checks["l2_disk_hit"]:
        raise RuntimeError("restart replay cache check failed: no cached usage or cross-process L2 disk-hit counter increment")
    if require_block_l2 and counters["block_l2_hits_delta"] <= 0:
        raise RuntimeError("restart replay cache check failed: no cross-process block L2 disk-hit counter increment")


def _ssm_rederive_stats(cache: dict[str, Any]) -> dict[str, Any]:
    direct = cache.get("ssm_companion")
    if isinstance(direct, dict) and isinstance(direct.get("rederive"), dict):
        return direct["rederive"]
    scheduler = cache.get("scheduler_cache")
    if isinstance(scheduler, dict):
        nested = scheduler.get("ssm_companion_cache")
        if isinstance(nested, dict) and isinstance(nested.get("rederive"), dict):
            return nested["rederive"]
    return {}


def _assert_ssm_rederive_behavior(
    report: dict[str, Any],
    replay_run_cache: dict[str, Any],
) -> None:
    rederive = _ssm_rederive_stats(replay_run_cache)
    requested = _int_at({"rederive": rederive}, ("rederive", "requested"))
    completed = _int_at({"rederive": rederive}, ("rederive", "completed"))
    failed = _int_at({"rederive": rederive}, ("rederive", "failed"))
    checks = {
        "requested": requested > 0,
        "completed": completed > 0,
        "no_failures": failed == 0,
        "state": rederive.get("state"),
        "reason": rederive.get("reason"),
        "last_num_tokens": rederive.get("last_num_tokens"),
    }
    report["ssm_rederive_checks"] = checks
    if not checks["requested"] or not checks["completed"] or not checks["no_failures"]:
        raise RuntimeError("ssm rederive check failed: expected requested/completed status without failures")


def _chat_completion(
    base_url: str,
    model_name: str,
    prompt: str,
    timeout: float,
    *,
    enable_thinking: bool,
) -> dict[str, Any]:
    return _request_json(
        "POST",
        f"{base_url}/v1/chat/completions",
        {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 16,
            "stream": False,
            "enable_thinking": enable_thinking,
            "chat_template_kwargs": {"enable_thinking": enable_thinking},
            "stream_options": {"include_usage": True},
        },
        timeout=timeout,
    )


def _launch_and_complete_once(
    *,
    path: Path,
    family: str,
    prompt: str,
    timeout: float,
    cache_root: Path,
    phase: str,
    enable_prompt_disk: bool = True,
) -> dict[str, Any]:
    port = _find_free_port()
    report: dict[str, Any] = {
        "phase": phase,
        "base_url": f"http://127.0.0.1:{port}",
        "launch_args": build_launch_args(path, port, cache_root=cache_root),
    }

    cmd = build_live_engine_command(
        path,
        port=port,
        cache_root=cache_root,
        enable_prompt_disk=enable_prompt_disk,
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ENGINE_DIR) + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    report["launch_command"] = cmd
    try:
        health = _wait_health(report["base_url"], timeout, proc=proc, report=report)
        models = _request_json("GET", f"{report['base_url']}/v1/models")
        model_name = health.get("model_name") or path.name
        smoke_thinking = family == "minimax"
        report["smoke_enable_thinking"] = smoke_thinking
        completion = _chat_completion(
            report["base_url"],
            model_name,
            prompt,
            timeout,
            enable_thinking=smoke_thinking,
        )
        cache = _request_json("GET", f"{report['base_url']}/v1/cache/stats")
        _assert_runtime_metadata(report, health, models, cache)
        _assert_completion(completion)
        report.update({
            "health": health,
            "models": models,
            "completion_usage": completion.get("usage", {}),
            "completion_preview": json.dumps(completion.get("choices", []))[:500],
            "cache_stats": cache,
            "completion": completion,
        })
        return report
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        if proc.stdout and "engine_log_tail" not in report:
            report["engine_log_tail"] = "".join(proc.stdout.readlines()[-60:])


def verify_live_model(
    path: str | Path,
    family: str,
    prompt: str,
    timeout: float,
    metadata_only: bool = False,
    restart_replay: bool = False,
    block_l2_only_replay: bool = False,
    require_ssm_rederive: bool = False,
) -> dict[str, Any]:
    port = _find_free_port()
    path = Path(path).expanduser().resolve()
    report = inspect_model_folder(path, expected_family=family)
    report["metadata_only"] = metadata_only
    report["restart_replay"] = restart_replay
    report["block_l2_only_replay"] = block_l2_only_replay
    report["require_ssm_rederive"] = require_ssm_rederive

    if not report["expected_ok"]:
        raise RuntimeError(f"{path} is {report['family']}, expected {family}")
    if family in {"qwen", "minimax"} and not report["supported"]:
        raise RuntimeError(f"{path} is not a supported Qwen/MiniMax folder")
    if metadata_only:
        report["launch_args"] = build_launch_args(path, port)
        return report

    cache_tmp = tempfile.TemporaryDirectory(prefix=f"exploitbot-{family}-live-cache-")
    cache_root = Path(cache_tmp.name)
    report["cache_root"] = "temporary"
    report["launch_args"] = build_launch_args(path, port, cache_root=cache_root)

    if restart_replay or block_l2_only_replay:
        try:
            first_run = _launch_and_complete_once(
                path=path,
                family=family,
                prompt=prompt,
                timeout=timeout,
                cache_root=cache_root,
                phase="populate",
                enable_prompt_disk=not block_l2_only_replay,
            )
            replay_run = _launch_and_complete_once(
                path=path,
                family=family,
                prompt=prompt,
                timeout=timeout,
                cache_root=cache_root,
                phase="replay",
                enable_prompt_disk=not block_l2_only_replay,
            )
            report.update({
                "first_run": first_run,
                "replay_run": replay_run,
                "completion_usage": first_run.get("completion_usage", {}),
                "cache_stats": first_run.get("cache_stats", {}),
                "replay_completion_usage": replay_run.get("completion_usage", {}),
                "replay_cache_stats": replay_run.get("cache_stats", {}),
            })
            _assert_restart_replay_cache_behavior(
                report,
                first_run_cache=first_run.get("cache_stats", {}),
                replay_run_cache=replay_run.get("cache_stats", {}),
                replay_completion=replay_run.get("completion", {}),
                require_block_l2=block_l2_only_replay,
            )
            if require_ssm_rederive:
                _assert_ssm_rederive_behavior(
                    report,
                    replay_run_cache=replay_run.get("cache_stats", {}),
                )
            return report
        except Exception as exc:
            raise VerificationError(f"{family} restart replay verification failed: {exc}", {family: report}) from exc
        finally:
            cache_tmp.cleanup()

    cmd = [
        _engine_python(),
        str(LAUNCH_PY),
        "--model",
        str(path),
        "--port",
        str(port),
        "--reasoning-parser",
        "auto",
        "--tool-call-parser",
        "auto",
        "--kv-cache-quantization",
        "turboquant-q4",
        "--enable-prefix-cache",
        "true",
        "--enable-disk-cache",
        "true",
        "--disk-cache-dir",
        str(cache_root / "prompt"),
        "--use-paged-cache",
        "true",
        "--enable-block-disk-cache",
        "true",
        "--block-disk-cache-dir",
        str(cache_root / "block"),
        "--max-tokens",
        "64",
        "--verbose",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ENGINE_DIR) + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    base_url = f"http://127.0.0.1:{port}"
    report["base_url"] = base_url
    report["launch_command"] = cmd
    try:
        health = _wait_health(base_url, timeout, proc=proc, report=report)
        models = _request_json("GET", f"{base_url}/v1/models")
        model_name = health.get("model_name") or path.name
        smoke_thinking = family == "minimax"
        report["smoke_enable_thinking"] = smoke_thinking
        completion = _chat_completion(
            base_url,
            model_name,
            prompt,
            timeout,
            enable_thinking=smoke_thinking,
        )
        cache = _request_json("GET", f"{base_url}/v1/cache/stats")
        repeat_completion = _chat_completion(
            base_url,
            model_name,
            prompt,
            timeout,
            enable_thinking=smoke_thinking,
        )
        repeat_cache = _request_json("GET", f"{base_url}/v1/cache/stats")
        _assert_runtime_metadata(report, health, models, cache)
        report.update({
            "health": health,
            "models": models,
            "completion_usage": completion.get("usage", {}),
            "completion_preview": json.dumps(completion.get("choices", []))[:500],
            "cache_stats": cache,
            "repeat_completion_usage": repeat_completion.get("usage", {}),
            "repeat_completion_preview": json.dumps(repeat_completion.get("choices", []))[:500],
            "repeat_cache_stats": repeat_cache,
        })
        _assert_completion(completion)
        _assert_completion(repeat_completion)
        _assert_repeat_cache_behavior(report, cache, repeat_cache, repeat_completion)
        return report
    except Exception as exc:
        raise VerificationError(f"{family} live verification failed: {exc}", {family: report}) from exc
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        if proc.stdout and "engine_log_tail" not in report:
            report["engine_log_tail"] = "".join(proc.stdout.readlines()[-60:])
        cache_tmp.cleanup()


def run(args: argparse.Namespace) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    if args.qwen:
        reports["qwen"] = verify_live_model(args.qwen, "qwen", args.prompt, args.timeout, args.metadata_only, args.restart_replay, args.block_l2_only_replay, args.require_ssm_rederive)
    if args.minimax:
        reports["minimax"] = verify_live_model(args.minimax, "minimax", args.prompt, args.timeout, args.metadata_only, args.restart_replay, args.block_l2_only_replay, args.require_ssm_rederive)
    if args.unsupported:
        reports["unsupported"] = inspect_model_folder(args.unsupported, expected_family="unsupported")
        if reports["unsupported"]["supported"]:
            raise RuntimeError(f"unsupported fixture is supported: {args.unsupported}")
    if not reports:
        raise RuntimeError("provide --qwen, --minimax, and/or --unsupported")
    return reports


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify ExploitBot Qwen/MiniMax model folders against the embedded vMLX engine.")
    parser.add_argument("--qwen", help="Qwen model folder to verify")
    parser.add_argument("--minimax", help="MiniMax model folder to verify")
    parser.add_argument("--unsupported", help="Unsupported model folder expected to be rejected by family preflight")
    parser.add_argument("--metadata-only", action="store_true", help="Only inspect folders and launch arguments; do not start the engine")
    parser.add_argument("--restart-replay", action="store_true", help="Run two engine processes against the same cache root and require cross-process L2 cache-hit evidence")
    parser.add_argument("--block-l2-only-replay", action="store_true", help="Run restart replay with prompt L2 disabled so replay must hit block L2 disk cache")
    parser.add_argument("--require-ssm-rederive", action="store_true", help="Require replay cache stats to show SSM rederive requested and completed without failures")
    parser.add_argument("--timeout", type=float, default=900.0, help="Seconds to wait for each live model to load/respond")
    parser.add_argument("--prompt", default="Reply with one short sentence for an ExploitBot cache/parser smoke test.")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()

    try:
        reports = run(args)
    except VerificationError as exc:
        if args.output:
            text = json.dumps({"ok": False, "error": str(exc), "reports": exc.reports}, indent=2, sort_keys=True)
            Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"verify-live-models failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        if args.output:
            text = json.dumps({"ok": False, "error": str(exc), "reports": {}}, indent=2, sort_keys=True)
            Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"verify-live-models failed: {exc}", file=sys.stderr)
        return 1

    text = json.dumps({"ok": True, "reports": reports}, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
