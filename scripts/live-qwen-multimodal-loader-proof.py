#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "ExploitBotEngine"
LAUNCH = ENGINE / "launch.py"
DEFAULT_OUTPUT = ROOT / "docs" / "live-proofs" / "live-qwen-multimodal-loader-proof.json"
TINY_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def fail(message: str) -> None:
    raise SystemExit(f"live-qwen-multimodal-loader proof failed: {message}")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:
        fail(f"could not read {path}: {exc}")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request_json(method: str, url: str, body: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def model_family_and_mode(model: Path) -> tuple[str, str, dict[str, Any]]:
    config = read_json(model / "config.json")
    jang = read_json(model / "jang_config.json")
    haystack = " ".join(
        [
            str(model).lower(),
            str(config.get("model_type", "")).lower(),
            str(config.get("architectures", "")).lower(),
            str((config.get("text_config") or {}).get("model_type", "")).lower(),
            str(jang.get("model_type", "")).lower(),
        ]
    )

    if "zaya" in haystack:
        fail("ZAYA folders are outside this beta lane; use an explicit Qwen/MiniMax multimodal folder")

    if "qwen" in haystack:
        family = "qwen"
    elif "minimax" in haystack or "mini_max" in haystack:
        family = "minimax"
    else:
        fail("model must be an explicit Qwen or MiniMax multimodal folder")

    explicit_markers = (
        "-vl",
        "_vl",
        "vlm",
        "qwen3-vl",
        "qwen3_vl",
        "qwen2-vl",
        "qwen2_vl",
        "qwen2.5-vl",
        "qwen2_5_vl",
        "minimax-vl",
        "minimax_vl",
    )
    model_type = str(config.get("model_type", "")).lower()
    architectures = " ".join(str(item).lower() for item in config.get("architectures", []))
    has_vision = "vision_config" in config
    jang_vision = (jang.get("architecture") or {}).get("has_vision") is True or jang.get("has_vision") is True
    explicit_vl = any(marker in haystack for marker in explicit_markers)
    model_type_vl = model_type in {"qwen3_vl", "qwen3_vl_moe", "qwen2_vl", "qwen2_5_vl", "minimax_vl"}
    architecture_vl = "vl" in architectures or "vision" in architectures

    if family == "qwen" and (
        "qwen3.5" in haystack
        or "qwen3.6" in haystack
        or model_type in {"qwen3_5", "qwen3_5_moe"}
    ) and not (explicit_vl or model_type_vl):
        fail("Qwen3.5/3.6 text-lane folders with vision_config are rejected unless the path or model_type is explicitly VL")

    if not (explicit_vl or model_type_vl or architecture_vl or has_vision or jang_vision):
        fail("model config does not expose an explicit multimodal/VL signal")

    mode = "explicit-vl" if (explicit_vl or model_type_vl) else "vision-config"
    return family, mode, {"config": config, "jang": jang}


def wait_for_engine(base_url: str, proc: subprocess.Popen[str], timeout: float) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"engine exited before health was ready with code {proc.returncode}")
        try:
            health = request_json("GET", f"{base_url}/health", timeout=3.0)
            if health:
                return health
        except Exception as exc:
            last_error = exc
        time.sleep(1.0)
    raise RuntimeError(f"engine did not become healthy before timeout: {last_error}")


def completion_text(completion: dict[str, Any]) -> str:
    choices = completion.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content") or message.get("reasoning_content") or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Live Qwen/MiniMax multimodal loader proof")
    parser.add_argument("--model", default=os.environ.get("EXPLOITBOT_LIVE_QWEN_MULTIMODAL_MODEL"))
    parser.add_argument("--output", default=os.environ.get("EXPLOITBOT_LIVE_QWEN_MULTIMODAL_OUTPUT", str(DEFAULT_OUTPUT)))
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("EXPLOITBOT_LIVE_QWEN_MULTIMODAL_TIMEOUT", "300")))
    args = parser.parse_args()

    if not args.model:
        fail("set EXPLOITBOT_LIVE_QWEN_MULTIMODAL_MODEL or pass --model; no artifact was written")

    model = Path(args.model).expanduser()
    output = Path(args.output).expanduser()
    if not model.is_dir():
        fail(f"model folder does not exist: {model}")
    if not LAUNCH.is_file():
        fail(f"engine launcher is missing: {LAUNCH}")

    family, mode, configs = model_family_and_mode(model)
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    python = ENGINE / ".venv" / "bin" / "python"
    if not python.is_file():
        python = Path(sys.executable)

    home = tempfile.TemporaryDirectory(prefix="exploitbot-qwen-multimodal-loader-home-")
    env = {
        **os.environ,
        "HOME": home.name,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(ENGINE) + (":" + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),
    }
    cmd = [
        str(python),
        str(LAUNCH),
        "--model",
        str(model),
        "--port",
        str(port),
        "--max-tokens",
        "8",
        "--max-num-seqs",
        "1",
        "--cache-memory-percent",
        "0.10",
        "--enable-disk-cache",
        "false",
        "--enable-block-disk-cache",
        "false",
    ]
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "live-qwen-multimodal-loader",
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "model": str(model),
        "family": family,
        "multimodalMode": mode,
        "engineCommand": cmd,
    }
    try:
        health = wait_for_engine(base_url, proc, args.timeout)
        model_name = health.get("model_name") or model.name
        message = {
            "role": "user",
            "content": [
                {"type": "text", "text": "Reply with exactly: VL-OK"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{TINY_PNG}"}},
            ],
        }
        completion = request_json(
            "POST",
            f"{base_url}/v1/chat/completions",
            {
                "model": model_name,
                "messages": [message],
                "max_tokens": 8,
                "stream": False,
                "enable_thinking": False,
                "chat_template_kwargs": {"enable_thinking": False},
                "stream_options": {"include_usage": True},
            },
            timeout=args.timeout,
        )
        text = completion_text(completion)
        if not text:
            fail("multimodal chat completion was empty; no artifact was written")
        cache_stats = request_json("GET", f"{base_url}/v1/cache/stats", timeout=10.0)
        engine_stats = request_json("GET", f"{base_url}/stats", timeout=10.0)
        report.update(
            {
                "ok": True,
                "loaded": True,
                "baseURL": base_url,
                "health": health,
                "configSummary": {
                    "model_type": configs["config"].get("model_type"),
                    "architectures": configs["config"].get("architectures", []),
                    "has_vision_config": "vision_config" in configs["config"],
                    "jang_has_vision": (configs["jang"].get("architecture") or {}).get("has_vision") or configs["jang"].get("has_vision"),
                },
                "completionPreview": text[:300],
                "usage": completion.get("usage", {}),
                "cacheStats": cache_stats,
                "engineStats": engine_stats,
            }
        )
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        home.cleanup()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"live-qwen-multimodal-loader proof passed: {output}")


if __name__ == "__main__":
    main()
