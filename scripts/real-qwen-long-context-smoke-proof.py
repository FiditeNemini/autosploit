#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import concurrent.futures
import json
import os
import re
import signal
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
MODEL_27B = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP")
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-real-qwen-long-context-smoke-27b.json"
DEFAULT_MARKER = "LONG_CONTEXT_SMOKE_PASS"


class CompletionMemoryGuardAbort(RuntimeError):
    def __init__(self, message: str, report: dict[str, Any]):
        super().__init__(message)
        self.report = report


def load_live_batch_module():
    path = ROOT / "scripts" / "prove-live-continuous-batching.py"
    spec = importlib.util.spec_from_file_location("exploitbot_live_batch", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load live batch helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def engine_python() -> str:
    override = os.environ.get("EXPLOITBOT_ENGINE_PYTHON")
    if override:
        return override
    venv_python = ENGINE_DIR / ".venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def ensure_tokenizer_runtime() -> None:
    try:
        import transformers  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    venv_python = ENGINE_DIR / ".venv" / "bin" / "python3"
    already_reexeced = os.environ.get("EXPLOITBOT_LONG_CONTEXT_REEXECED") == "1"
    if venv_python.exists() and not already_reexeced:
        env = os.environ.copy()
        env["EXPLOITBOT_LONG_CONTEXT_REEXECED"] = "1"
        os.execve(str(venv_python), [str(venv_python), *sys.argv], env)

    raise ModuleNotFoundError(
        "transformers is required for tokenizer-counted long-context proof; "
        f"engine venv was not usable at {venv_python}"
    )


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request_json(method: str, url: str, body: dict[str, Any] | None = None, timeout: float = 30.0) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {
                "status": resp.status,
                "json": json.loads(resp.read().decode("utf-8")),
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            payload: Any = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return {"status": exc.code, "json": payload}


def memory_pressure_sample() -> dict[str, Any]:
    proc = subprocess.run(
        ["/usr/bin/memory_pressure"],
        text=True,
        capture_output=True,
        timeout=10.0,
    )
    output = proc.stdout + proc.stderr
    free_match = re.search(r"System-wide memory free percentage:\s*(\d+)%", output)
    swapout_match = re.search(r"Swapouts:\s*(\d+)", output)
    free_percent = int(free_match.group(1)) if free_match else None
    swapouts = int(swapout_match.group(1)) if swapout_match else None
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "freePercent": free_percent,
        "swapouts": swapouts,
    }


def completion_memory_abort_free_percent(target_prompt_tokens: int) -> int:
    override = os.environ.get("EXPLOITBOT_LONG_CONTEXT_ABORT_FREE_PERCENT")
    if override:
        return max(0, int(override))
    if target_prompt_tokens >= 160_000:
        return 15
    if target_prompt_tokens >= 128_000:
        return 12
    return 0


def completion_memory_sample_interval(target_prompt_tokens: int) -> float:
    override = os.environ.get("EXPLOITBOT_LONG_CONTEXT_MEMORY_SAMPLE_INTERVAL")
    if override:
        return float(override)
    if target_prompt_tokens >= 192_000:
        return 1.0
    if target_prompt_tokens >= 160_000:
        return 2.0
    return 5.0


def guarded_completion_request(
    *,
    method: str,
    url: str,
    body: dict[str, Any],
    timeout: float,
    engine: subprocess.Popen[str] | None,
    base_url: str,
    target_prompt_tokens: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    abort_free_percent = completion_memory_abort_free_percent(target_prompt_tokens)
    interval = completion_memory_sample_interval(target_prompt_tokens)
    baseline_sample = memory_pressure_sample()
    baseline_swapouts = baseline_sample.get("swapouts")
    report: dict[str, Any] = {
        "guardKind": "completionMemory",
        "enabled": abort_free_percent > 0,
        "abortFreePercent": abort_free_percent,
        "sampleIntervalSeconds": interval,
        "baselineSample": baseline_sample,
        "samples": [],
        "aborted": False,
    }
    if abort_free_percent <= 0:
        response = request_json(method, url, body, timeout=timeout)
        return response, report

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(request_json, method, url, body, timeout)
    try:
        while not future.done():
            sample = memory_pressure_sample()
            current_swapouts = sample.get("swapouts")
            swapouts_delta = 0
            if isinstance(current_swapouts, int) and isinstance(baseline_swapouts, int):
                swapouts_delta = max(0, current_swapouts - baseline_swapouts)
            sample["swapoutsDelta"] = swapouts_delta
            report["samples"].append(sample)
            free_percent = sample.get("freePercent")
            if (isinstance(free_percent, int) and free_percent < abort_free_percent) or (
                swapouts_delta > 0
            ):
                report["aborted"] = True
                report["abortReason"] = (
                    "free_memory_below_threshold"
                    if isinstance(free_percent, int) and free_percent < abort_free_percent
                    else "new_swapouts_detected"
                )
                try:
                    report["cacheAtAbort"] = request_json(
                        "GET",
                        f"{base_url}/v1/cache/stats",
                        timeout=5.0,
                    ).get("json")
                except Exception as exc:
                    report["cacheAtAbortError"] = f"{type(exc).__name__}: {exc}"
                terminate_process_group(engine)
                raise CompletionMemoryGuardAbort(
                    "long-context completion memory guard aborted the engine",
                    report,
                )
            time.sleep(interval)
        return future.result(), report
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def wait_health(base_url: str, proc: subprocess.Popen[str], timeout: float = 420.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_error: Any = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"engine exited before health: exit={proc.returncode}\n{read_tail(proc)}")
        try:
            response = request_json("GET", f"{base_url}/health", timeout=8.0)
            health = response.get("json") or {}
            if response.get("status") == 200 and health.get("status") == "healthy":
                return health
            last_error = health
        except Exception as exc:
            last_error = exc
        time.sleep(1.0)
    raise RuntimeError(f"engine did not become healthy: {last_error}")


def read_tail(proc: subprocess.Popen[str] | None, max_lines: int = 180) -> str:
    if proc is None:
        return ""
    log_path = getattr(proc, "exploitbot_log_path", None)
    if log_path is not None:
        try:
            text = Path(log_path).read_text(encoding="utf-8", errors="replace")
            return "\n".join(text.splitlines()[-max_lines:])
        except Exception as exc:
            return f"<unable to read process log {log_path}: {exc}>"
    if proc.stdout is None:
        return ""
    try:
        text = proc.stdout.read()
    except Exception as exc:
        return f"<unable to read process output: {exc}>"
    return "\n".join(text.splitlines()[-max_lines:])


def terminate_process_group(proc: subprocess.Popen[str] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception:
        proc.terminate()
    try:
        proc.wait(timeout=12.0)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except Exception:
            proc.kill()
        proc.wait(timeout=5.0)


def model_context_contract(model: Path) -> dict[str, Any]:
    config = json.loads((model / "config.json").read_text(encoding="utf-8"))
    tokenizer_config = json.loads((model / "tokenizer_config.json").read_text(encoding="utf-8"))
    text_config = config.get("text_config") or {}
    return {
        "configTextMaxPositionEmbeddings": text_config.get("max_position_embeddings"),
        "tokenizerModelMaxLength": tokenizer_config.get("model_max_length"),
        "modelType": config.get("model_type"),
        "textModelType": text_config.get("model_type"),
        "ropeParameters": text_config.get("rope_parameters"),
    }


def load_tokenizer(model: Path):
    ensure_tokenizer_runtime()
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(str(model), trust_remote_code=True, local_files_only=True)


def token_count(tokenizer: Any, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def long_context_line(index: int) -> str:
    return (
        f"CTX-LONG-{index:05d}: scoped localhost lab note, cache-prefix sentinel, "
        f"paged-block marker, hybrid-ssm rederive sentinel {index % 97}.\n"
    )


def assemble_long_prompt(intro: str, outro: str, line_count: int) -> str:
    return intro + "".join(long_context_line(i) for i in range(line_count)) + outro


def build_long_prompt(tokenizer: Any, target_tokens: int, marker: str) -> tuple[str, int]:
    intro = (
        "You are running a long-context smoke test for ExploitBot. "
        "Do not call tools. At the end, reply exactly with the marker "
        f"{marker} and nothing else.\n\n"
    )
    outro = f"\n\nFinal instruction: reply exactly {marker}"
    base_tokens = token_count(tokenizer, intro + outro)
    if base_tokens >= target_tokens:
        prompt = intro + outro
        return prompt, base_tokens

    sample_lines = 32
    sample_prompt = assemble_long_prompt("", "", sample_lines)
    sample_tokens = max(1, token_count(tokenizer, sample_prompt))
    estimated_line_tokens = max(1.0, sample_tokens / sample_lines)
    high = max(1, int((target_tokens - base_tokens) / estimated_line_tokens))
    prompt = assemble_long_prompt(intro, outro, high)
    high_tokens = token_count(tokenizer, prompt)

    while high_tokens < target_tokens:
        remaining = target_tokens - high_tokens
        add = max(1, int(remaining / estimated_line_tokens) + 1)
        high += add
        prompt = assemble_long_prompt(intro, outro, high)
        high_tokens = token_count(tokenizer, prompt)

    low = 0
    while low < high:
        mid = (low + high) // 2
        mid_tokens = token_count(tokenizer, assemble_long_prompt(intro, outro, mid))
        if mid_tokens >= target_tokens:
            high = mid
        else:
            low = mid + 1

    prompt = assemble_long_prompt(intro, outro, low)
    return prompt, token_count(tokenizer, prompt)


def launch_engine(model: Path, port: int, cache_root: Path, max_prompt_tokens: int) -> subprocess.Popen[str]:
    server_timeout = os.environ.get("EXPLOITBOT_LONG_CONTEXT_SERVER_TIMEOUT") or os.environ.get(
        "EXPLOITBOT_LONG_CONTEXT_TIMEOUT",
        "900",
    )
    cmd = [
        engine_python(),
        str(LAUNCH_PY),
        "--model",
        str(model),
        "--port",
        str(port),
        "--timeout",
        str(server_timeout),
        "--reasoning-parser",
        "qwen3",
        "--tool-call-parser",
        "qwen",
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
        "32",
        "--max-prompt-tokens",
        str(max_prompt_tokens),
        "--max-num-seqs",
        "1",
        "--cache-memory-percent",
        "0.20",
        "--verbose",
    ]
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ENGINE_DIR) + (":" + existing if existing else "")
    cache_root.mkdir(parents=True, exist_ok=True)
    log_path = cache_root / "engine.log"
    log_file = log_path.open("w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
    except BaseException:
        log_file.close()
        raise
    log_file.close()
    proc.exploitbot_log_path = log_path  # type: ignore[attr-defined]
    return proc


def chat_body(model: Path, prompt: str, marker: str, max_prompt_tokens: int | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": str(model),
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 32,
        "temperature": 0,
        "top_p": 1,
        "stream": False,
        "enable_thinking": False,
        "chat_template_kwargs": {"enable_thinking": False},
        "stream_options": {"include_usage": True},
    }
    if max_prompt_tokens is not None:
        body["max_prompt_tokens"] = max_prompt_tokens
    return body


def completion_text(completion: dict[str, Any]) -> str:
    parts: list[str] = []
    for choice in completion.get("choices") or []:
        message = choice.get("message") or {}
        if message.get("content"):
            parts.append(str(message["content"]))
        if message.get("reasoning_content"):
            parts.append(str(message["reasoning_content"]))
    return "\n".join(parts)


def q4_kv_enabled(value: Any) -> bool:
    if value == "turboquant-q4":
        return True
    if isinstance(value, dict):
        return value.get("enabled") is True and int(value.get("bits") or 0) == 4
    return False


def turboquant_q4_kv_enabled(health: dict[str, Any], after_cache: dict[str, Any]) -> bool:
    effective_cache = ((health.get("effective_config") or {}).get("cache") or {})
    effective_kvq = effective_cache.get("kv_cache_quantization") or {}
    after_kvq = after_cache.get("kv_cache_quantization") or {}
    return (
        effective_kvq.get("enabled") is True
        and str(effective_kvq.get("mode") or "").startswith("turboquant-")
        and after_kvq.get("enabled") is True
        and int(after_kvq.get("bits") or 0) == 4
    )


def ssm_companion_not_quantized(after_cache: dict[str, Any]) -> bool:
    native_cache = after_cache.get("native_cache") or {}
    storage_quant = native_cache.get("attention_kv_storage_quantization") or {}
    return (
        storage_quant.get("enabled") is True
        and storage_quant.get("applies_to") == "attention_kv_layers_only"
        and storage_quant.get("ssm_policy") == "native_companion_state"
        and storage_quant.get("rederive") == "async_clean_prefill_on_miss_or_warm_pass"
    )


def required_available_memory_for_target_gb(live_batch: Any, model: Path, target_prompt_tokens: int) -> float:
    override = os.environ.get("EXPLOITBOT_LONG_CONTEXT_MIN_AVAILABLE_GB")
    if override:
        return float(override)
    base_required = float(live_batch.required_available_memory_gb(model, 1))
    if target_prompt_tokens >= 250_000:
        return max(base_required, 80.0)
    if target_prompt_tokens >= 192_000:
        return max(base_required, 72.0)
    if target_prompt_tokens >= 160_000:
        return max(base_required, 68.0)
    if target_prompt_tokens >= 128_000:
        return max(base_required, 64.0)
    if target_prompt_tokens >= 64_000:
        return max(base_required, 56.0)
    return base_required


def proven_safe_target_ceiling() -> int:
    override = os.environ.get("EXPLOITBOT_LONG_CONTEXT_PROVEN_SAFE_TARGET_CEILING")
    if override:
        return int(override)
    return 192_000


def allow_unproven_near_max_target() -> bool:
    return os.environ.get("EXPLOITBOT_LONG_CONTEXT_ALLOW_UNPROVEN_TARGET") == "1"


def target_context_memory_preflight(live_batch: Any, model: Path, target_prompt_tokens: int) -> dict[str, Any]:
    if os.environ.get("EXPLOITBOT_LONG_CONTEXT_SKIP_TARGET_MEMORY_GUARD") == "1":
        return {
            "enabled": False,
            "skippedBy": "EXPLOITBOT_LONG_CONTEXT_SKIP_TARGET_MEMORY_GUARD",
            "targetPromptTokens": target_prompt_tokens,
        }

    wait_seconds = float(os.environ.get("EXPLOITBOT_LONG_CONTEXT_WAIT_FOR_MEMORY_SLOT_SECONDS", "0") or 0)
    wait_interval = float(os.environ.get("EXPLOITBOT_LONG_CONTEXT_WAIT_FOR_MEMORY_SLOT_INTERVAL", "15") or 15)
    wait_deadline = time.time() + max(0.0, wait_seconds)
    wait_report: dict[str, Any] = {
        "enabled": wait_seconds > 0,
        "timeoutSeconds": wait_seconds,
        "sampleIntervalSeconds": wait_interval,
        "samples": [],
    }

    while True:
        report = target_context_memory_preflight_report(
            live_batch,
            model,
            target_prompt_tokens,
        )
        report["memorySlotWait"] = wait_report
        block_reason = target_context_preflight_block_reason(report)
        if block_reason is None:
            return report
        if wait_seconds > 0 and time.time() < wait_deadline:
            wait_report["samples"].append({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "blockReason": block_reason,
                "availableGB": report.get("availableGB"),
                "targetRequiredAvailableGB": report.get("targetRequiredAvailableGB"),
                "heavyModelProcessCount": report.get("heavyModelProcessCount"),
                "heavyModelProcesses": (report.get("heavyModelProcesses") or [])[:3],
            })
            remaining = max(0.0, wait_deadline - time.time())
            time.sleep(min(wait_interval, remaining))
            continue

        wait_report["timedOut"] = wait_seconds > 0
        wait_report["lastBlockReason"] = block_reason
        if block_reason == "unproven_target_above_safe_ceiling":
            raise live_batch.MemoryPreflightError(
                "long-context target preflight refused to start above the proven safe target ceiling; "
                "set EXPLOITBOT_LONG_CONTEXT_ALLOW_UNPROVEN_TARGET=1 only for an intentional high-risk proof run",
                report,
            )
        if block_reason == "heavy_model_processes":
            raise live_batch.MemoryPreflightError(
                "long-context target preflight refused to stack this run on another heavyweight model/eval process",
                report,
            )
        raise live_batch.MemoryPreflightError(
            "long-context target preflight refused to start with insufficient available memory for target prompt tokens",
            report,
        )


def target_context_memory_preflight_report(live_batch: Any, model: Path, target_prompt_tokens: int) -> dict[str, Any]:
    available_gb = live_batch.current_available_memory_gb()
    heavy_processes = live_batch.current_heavy_model_processes()
    allow_concurrent = os.environ.get("EXPLOITBOT_LIVE_BATCH_ALLOW_CONCURRENT_MODEL") == "1"
    model_required_gb = float(live_batch.required_available_memory_gb(model, 1))
    target_required_gb = required_available_memory_for_target_gb(live_batch, model, target_prompt_tokens)
    return {
        "preflightKind": "targetContext",
        "enabled": True,
        "targetPromptTokens": target_prompt_tokens,
        "provenSafeTargetCeiling": proven_safe_target_ceiling(),
        "allowUnprovenNearMaxTarget": allow_unproven_near_max_target(),
        "unprovenTargetOverrideEnv": "EXPLOITBOT_LONG_CONTEXT_ALLOW_UNPROVEN_TARGET",
        "availableGB": available_gb,
        "modelRequiredAvailableGB": model_required_gb,
        "targetRequiredAvailableGB": target_required_gb,
        "heavyModelProcessCount": len(heavy_processes),
        "heavyModelProcesses": heavy_processes[:8],
        "allowConcurrentModel": allow_concurrent,
    }


def target_context_preflight_block_reason(report: dict[str, Any]) -> str | None:
    target_tokens = report.get("targetPromptTokens")
    safe_ceiling = report.get("provenSafeTargetCeiling")
    if (
        isinstance(target_tokens, int)
        and isinstance(safe_ceiling, int)
        and target_tokens > safe_ceiling
        and report.get("allowUnprovenNearMaxTarget") is not True
    ):
        return "unproven_target_above_safe_ceiling"
    if report.get("heavyModelProcessCount", 0) and not report.get("allowConcurrentModel"):
        return "heavy_model_processes"
    available_gb = report.get("availableGB")
    required_gb = report.get("targetRequiredAvailableGB")
    if (
        isinstance(available_gb, (int, float))
        and isinstance(required_gb, (int, float))
        and available_gb < required_gb
    ):
        return "insufficient_available_memory"
    return None


def proof_scope_for_target(target_prompt_tokens: int) -> str:
    if target_prompt_tokens >= 250_000:
        return "near-max 262144-token context stress proof with explicit RAM/process guard"
    return "long-context smoke, not a full 262144-token max-context proof"


def positive_stat(value: Any, *keys: str) -> bool:
    if not isinstance(value, dict):
        return False
    for key in keys:
        found = value.get(key)
        if isinstance(found, (int, float)) and found > 0:
            return True
    return False


def evaluate_long_context_status(
    *,
    declared: dict[str, Any],
    health: dict[str, Any],
    after_cache: dict[str, Any],
    completion_response: dict[str, Any],
    text: str,
    usage: dict[str, Any],
    marker: str,
    target_prompt_tokens: int,
    session_cap: int,
) -> dict[str, str]:
    native_cache = after_cache.get("native_cache") or {}
    cache_totals = after_cache.get("cache_totals") or {}
    block_cache = after_cache.get("block_disk_cache") or {}
    return {
        "declared262kContext": "PASS" if declared.get("configTextMaxPositionEmbeddings") == 262144 and declared.get("tokenizerModelMaxLength") == 262144 else "FAIL",
        "engineSessionPromptCap": "PASS" if health.get("max_prompt_tokens") == session_cap else "FAIL",
        "lowerPerRequestCapRejected": "PASS",
        "longPromptCompleted": "PASS" if completion_response.get("status") == 200 and marker in text else "FAIL",
        "usagePromptTokensReported": "PASS" if int(usage.get("prompt_tokens") or 0) >= target_prompt_tokens else "FAIL",
        "q4TurboQuantKV": "PASS" if turboquant_q4_kv_enabled(health, after_cache) else "FAIL",
        "q4KV": "PASS" if q4_kv_enabled(after_cache.get("kv_cache_quantization") or health.get("kv_cache_quantization")) else "FAIL",
        "ssmCompanionNotQuantized": "PASS" if ssm_companion_not_quantized(after_cache) else "FAIL",
        "pagedCache": "PASS" if native_cache.get("paged") is True else "FAIL",
        "prefixCache": "PASS" if native_cache.get("prefix") is True else "FAIL",
        "hybridSSM": "PASS" if native_cache.get("cache_type") == "hybrid_ssm_typed" and positive_stat(cache_totals, "ssm_tokens_on_disk", "l2_ssm_tokens_on_disk") else "FAIL",
        "blockL2": "PASS" if positive_stat(block_cache, "total_tokens_on_disk", "total_cached_tokens") or positive_stat(cache_totals, "l2_block_tokens_on_disk") else "FAIL",
    }


def main() -> None:
    model = Path(os.environ.get("EXPLOITBOT_LONG_CONTEXT_MODEL", str(MODEL_27B))).expanduser()
    output = Path(os.environ.get("EXPLOITBOT_LONG_CONTEXT_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    target_prompt_tokens = int(os.environ.get("EXPLOITBOT_LONG_CONTEXT_TARGET_TOKENS", "8192"))
    marker = os.environ.get("EXPLOITBOT_LONG_CONTEXT_MARKER", DEFAULT_MARKER)
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "real-qwen-long-context-smoke",
        "model": str(model),
        "targetPromptTokens": target_prompt_tokens,
        "marker": marker,
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "scope": proof_scope_for_target(target_prompt_tokens),
        "pythonExecutable": sys.executable,
        "reexecedIntoEngineVenv": os.environ.get("EXPLOITBOT_LONG_CONTEXT_REEXECED") == "1",
    }
    engine: subprocess.Popen[str] | None = None
    base_url: str | None = None
    cache_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-long-context-cache-")
    if not model.is_dir():
        report["error"] = f"Qwen model folder missing: {model}"
        report["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise AssertionError(report["error"])
    try:
        live_batch = load_live_batch_module()
        report["targetMemoryPreflight"] = target_context_memory_preflight(
            live_batch,
            model,
            target_prompt_tokens,
        )
        tokenizer = load_tokenizer(model)
        prompt, actual_prompt_tokens = build_long_prompt(tokenizer, target_prompt_tokens, marker)
        session_cap = max(actual_prompt_tokens + 2048, target_prompt_tokens + 2048)
        lower_cap = max(256, actual_prompt_tokens // 2)
        declared = model_context_contract(model)
        report.update({
            "actualPromptTokensByTokenizer": actual_prompt_tokens,
            "sessionMaxPromptTokens": session_cap,
            "lowerCapForRejection": lower_cap,
            "declaredContext": declared,
        })
        report["memoryPreflight"] = live_batch.live_batch_memory_preflight(model, 1)
        port = free_port()
        base_url = f"http://127.0.0.1:{port}"
        report["baseUrl"] = base_url
        engine = launch_engine(model, port, Path(cache_tmp.name), session_cap)
        health = wait_health(base_url, engine)
        report["health"] = health

        reject_response = request_json(
            "POST",
            f"{base_url}/v1/chat/completions",
            chat_body(model, prompt, marker, max_prompt_tokens=lower_cap),
            timeout=60.0,
        )
        report["lowerCapRejectResponse"] = reject_response
        if reject_response.get("status") != 413:
            raise AssertionError(f"expected lower per-request context cap rejection, got {reject_response}")

        before_cache = request_json("GET", f"{base_url}/v1/cache/stats", timeout=10.0).get("json") or {}
        completion_response, completion_memory_guard = guarded_completion_request(
            method="POST",
            url=f"{base_url}/v1/chat/completions",
            body=chat_body(model, prompt, marker),
            timeout=float(os.environ.get("EXPLOITBOT_LONG_CONTEXT_TIMEOUT", "900")),
            engine=engine,
            base_url=base_url,
            target_prompt_tokens=target_prompt_tokens,
        )
        after_cache = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0).get("json") or {}
        report["cacheBefore"] = before_cache
        report["completion"] = completion_response
        report["completionMemoryGuard"] = completion_memory_guard
        report["cacheAfter"] = after_cache

        completion = completion_response.get("json") or {}
        text = completion_text(completion)
        usage = completion.get("usage") or {}
        status = evaluate_long_context_status(
            declared=declared,
            health=health,
            after_cache=after_cache,
            completion_response=completion_response,
            text=text,
            usage=usage,
            marker=marker,
            target_prompt_tokens=target_prompt_tokens,
            session_cap=session_cap,
        )
        report["status"] = status
        report["usage"] = usage
        report["assistantPreview"] = text[:1200]
        if any(value != "PASS" for value in status.values()):
            raise AssertionError(f"long-context smoke failed status checks: {status}")

        report["ok"] = True
    except BaseException as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        if isinstance(exc, KeyboardInterrupt):
            report["interruptedBy"] = "KeyboardInterrupt"
        if base_url:
            try:
                report["cacheAtError"] = request_json("GET", f"{base_url}/v1/cache/stats", timeout=5.0).get("json")
            except Exception as cache_exc:
                report["cacheAtErrorError"] = f"{type(cache_exc).__name__}: {cache_exc}"
        if getattr(exc, "report", None) is not None:
            if exc.report.get("guardKind") == "completionMemory":
                report["completionMemoryGuard"] = exc.report
            else:
                preflight_key = "targetMemoryPreflight" if exc.report.get("preflightKind") == "targetContext" else "memoryPreflight"
                report[preflight_key] = exc.report
        raise
    finally:
        finished_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        report["finishedAt"] = finished_at
        report["generatedAt"] = report.get("generatedAt") or finished_at
        terminate_process_group(engine)
        report["engineLogTail"] = read_tail(engine)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        cache_tmp.cleanup()

    print(f"real-qwen long-context smoke proof wrote {output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"real-qwen long-context smoke proof failed: {exc}", flush=True)
        raise SystemExit(1)
