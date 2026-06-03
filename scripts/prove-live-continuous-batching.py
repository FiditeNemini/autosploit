#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = ROOT / "ExploitBotEngine"
LAUNCH_PY = ENGINE_DIR / "launch.py"
DEFAULT_QWEN = Path("/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP")
DEFAULT_MINIMAX = Path("/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ")
DEFAULT_OUTPUT = ROOT / "docs" / "live-proofs" / "checkpoint-452-qwen-continuous-batching-live.json"


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:4000]
        raise AssertionError(message + suffix)


def engine_python() -> str:
    override = os.environ.get("EXPLOITBOT_ENGINE_PYTHON")
    if override:
        return override
    venv_python = ENGINE_DIR / ".venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request_json(method: str, url: str, body: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def read_output_tail(proc: subprocess.Popen[str] | None, max_lines: int = 120) -> str:
    if proc is None or proc.stdout is None:
        return ""
    try:
        text = proc.stdout.read()
    except Exception as exc:
        return f"<unable to read engine output: {exc}>"
    return "\n".join(text.splitlines()[-max_lines:])


def wait_health(base_url: str, proc: subprocess.Popen[str], timeout: float = 420.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"engine exited before health: exit={proc.returncode}\n{read_output_tail(proc)}")
        try:
            health = request_json("GET", f"{base_url}/health", timeout=8.0)
            if health.get("status") == "healthy":
                return health
            last_error = RuntimeError(json.dumps(health, sort_keys=True)[:1000])
        except Exception as exc:
            last_error = exc
        time.sleep(1.0)
    raise RuntimeError(f"engine did not become healthy: {last_error}")


def completion_text(completion: dict[str, Any]) -> str:
    choices = completion.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content") or message.get("reasoning_content") or "")


def int_at(data: dict[str, Any], path: tuple[str, ...]) -> int:
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return 0
        value = value.get(key)
    return int(value or 0) if isinstance(value, (int, float)) else 0


def chat(base_url: str, model_name: str, prompt: str, barrier: threading.Barrier) -> dict[str, Any]:
    barrier.wait(timeout=20.0)
    started = time.time()
    completion = request_json(
        "POST",
        f"{base_url}/v1/chat/completions",
        {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 16,
            "stream": False,
            "temperature": 0,
            "top_p": 1,
            "enable_thinking": False,
            "chat_template_kwargs": {"enable_thinking": False},
            "stream_options": {"include_usage": True},
        },
        timeout=240.0,
    )
    return {
        "startedAt": started,
        "finishedAt": time.time(),
        "completion": completion,
        "textPreview": completion_text(completion)[:300],
        "usage": completion.get("usage", {}),
    }


def launch_engine(model: Path, port: int, cache_root: Path) -> subprocess.Popen[str]:
    cmd = [
        engine_python(),
        str(LAUNCH_PY),
        "--model",
        str(model),
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
        "32",
        "--max-num-seqs",
        "2",
        "--cache-memory-percent",
        "0.20",
        "--verbose",
    ]
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ENGINE_DIR) + (":" + existing_pp if existing_pp else "")
    return subprocess.Popen(
        cmd,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def main() -> None:
    family = os.environ.get("EXPLOITBOT_LIVE_BATCH_FAMILY", "qwen").lower()
    default_model = DEFAULT_MINIMAX if family == "minimax" else DEFAULT_QWEN
    model = Path(
        os.environ.get("EXPLOITBOT_LIVE_BATCH_MODEL")
        or os.environ.get("EXPLOITBOT_LIVE_BATCH_QWEN_MODEL")
        or os.environ.get("EXPLOITBOT_LIVE_BATCH_MINIMAX_MODEL")
        or str(default_model)
    ).expanduser()
    output = Path(os.environ.get("EXPLOITBOT_LIVE_BATCH_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    family_label = "MiniMax" if family == "minimax" else "Qwen"
    response_marker = "MINIMAX" if family == "minimax" else "QWEN"
    require(model.is_dir(), f"{family_label} model folder is missing: {model}")

    port = int(os.environ.get("EXPLOITBOT_LIVE_BATCH_PORT") or free_port())
    base_url = f"http://127.0.0.1:{port}"
    cache_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-live-batch-cache-")
    proc: subprocess.Popen[str] | None = None
    report: dict[str, Any] = {
        "model": str(model),
        "baseUrl": base_url,
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "proofType": f"live-{family}-continuous-batching",
        "family": family,
        "maxNumSeqs": 2,
    }

    try:
        proc = launch_engine(model, port, Path(cache_tmp.name))
        health = wait_health(base_url, proc)
        model_name = health.get("model_name") or model.name
        cache_before = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)

        effective = health.get("effective_config") or {}
        cache_config = effective.get("cache") or {}
        topology = cache_config.get("topology") or {}
        kv = cache_config.get("kv_cache_quantization") or {}
        require(health.get("engine_type") == "batched", "engine did not report BatchedEngine", health)
        require(topology.get("cache_type") in {"hybrid", "full_kv"}, "unexpected cache topology", health)
        require(kv.get("mode") == "turboquant-q4", "TurboQuant q4 KV cache not enabled", health)
        require((cache_config.get("prefix_cache") or {}).get("enabled") is True, "prefix cache not enabled", health)
        require((cache_config.get("paged_cache") or {}).get("enabled") is True, "paged cache not enabled", health)

        barrier = threading.Barrier(2)
        prompts = [
            f"Authorized batch test A. Reply with the exact text BATCH-{response_marker}-A.",
            f"Authorized batch test B. Reply with the exact text BATCH-{response_marker}-B.",
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(chat, base_url, model_name, prompt, barrier)
                for prompt in prompts
            ]
            results = [future.result(timeout=300.0) for future in futures]

        cache_after = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)
        scheduler = cache_after.get("scheduler_stats") or {}
        windows = [
            {"startedAt": item["startedAt"], "finishedAt": item["finishedAt"]}
            for item in results
        ]
        overlap = max(w["startedAt"] for w in windows) < min(w["finishedAt"] for w in windows)
        require(overlap, "client requests did not overlap", windows)
        require(all(item.get("textPreview") for item in results), "one or more completions were empty", results)
        require(int_at({"s": scheduler}, ("s", "num_requests_processed")) >= 2, "scheduler did not process both requests", scheduler)
        require(int_at({"s": scheduler}, ("s", "max_running_observed")) >= 2, "scheduler did not observe two running requests", scheduler)
        require(int_at(cache_after, ("kv_cache_quantization", "bits")) == 4, "KV cache quantization bits not reported as q4", cache_after)

        report.update(
            {
                "ok": True,
                "health": health,
                "cacheBefore": cache_before,
                "cacheAfter": cache_after,
                "schedulerStats": scheduler,
                "requestWindows": windows,
                "clientOverlap": overlap,
                "results": results,
            }
        )
    finally:
        if proc is not None and proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=15.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=15.0)
        cache_tmp.cleanup()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"live-{family}-continuous-batching proof passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"live-continuous-batching proof failed: {exc}", flush=True)
        raise SystemExit(1)
