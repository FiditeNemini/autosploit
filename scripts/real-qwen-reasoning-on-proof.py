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
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = ROOT / "ExploitBotEngine"
LAUNCH_PY = ENGINE_DIR / "launch.py"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
APP_API = "http://127.0.0.1:9999"
MODEL_27B = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP")
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-real-qwen-27b-reasoning-on.json"
DEFAULT_MARKER = "UI27-REASONING-LIVE-ACK"


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


def request_json(method: str, url: str, body: dict[str, Any] | str | None = None, timeout: float = 15.0) -> dict[str, Any]:
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def app_request(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 15.0) -> dict[str, Any]:
    return request_json(method, f"{APP_API}{path}", body, timeout=timeout)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_until(predicate, label: str, timeout: float = 60.0):
    deadline = time.time() + timeout
    last_value = None
    while time.time() < deadline:
        try:
            last_value = predicate()
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            last_value = None
        if last_value:
            return last_value
        time.sleep(0.5)
    raise AssertionError(f"timed out waiting for {label}; last={last_value}")


def wait_for_app(timeout: float = 20.0) -> None:
    wait_until(lambda: app_request("GET", "/state", timeout=1.0), "app test server", timeout=timeout)


def build_app_bundle() -> None:
    result = subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError("build_and_run --build-only failed")
    if not APP_BINARY.exists():
        raise RuntimeError(f"app binary missing after build: {APP_BINARY}")


def read_output_tail(proc: subprocess.Popen[str] | None, max_lines: int = 180) -> str:
    if proc is None or proc.stdout is None:
        return ""
    try:
        text = proc.stdout.read()
    except Exception as exc:
        return f"<unable to read process output: {exc}>"
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


def launch_engine(model: Path, port: int, cache_root: Path, max_tokens: int) -> subprocess.Popen[str]:
    cmd = [
        engine_python(),
        str(LAUNCH_PY),
        "--model",
        str(model),
        "--port",
        str(port),
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
        str(max_tokens),
        "--max-num-seqs",
        "1",
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
        start_new_session=True,
    )


def proof_prompt(marker: str) -> str:
    return (
        "Reasoning-on live Qwen proof. Do not run tools. "
        f"After reasoning, answer in final assistant content with exact marker {marker} "
        "and one short sentence."
    )


def wait_for_completion(timeout: float = 420.0) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    deadline = time.time() + timeout
    last: tuple[list[dict[str, Any]], dict[str, Any]] | None = None
    while time.time() < deadline:
        messages = app_request("GET", "/messages", timeout=5.0)
        state = app_request("GET", "/state", timeout=5.0)
        last = (messages, state)
        if not state.get("isWorking") and not state.get("isStreaming"):
            return messages, state
        time.sleep(1.0)
    raise AssertionError("timed out waiting for reasoning-on turn completion", {"last": last})


def classify(messages: list[dict[str, Any]], marker: str) -> dict[str, Any]:
    assistant_text = "\n".join(
        str(item.get("content") or "")
        for item in messages
        if item.get("role") == "assistant"
    )
    thinking_text = "\n".join(
        str(item.get("content") or "")
        for item in messages
        if item.get("role") == "thinking"
    )
    assistant_has_marker = marker in assistant_text
    thinking_has_marker = marker in thinking_text
    warning = "No final assistant content was produced" in assistant_text
    if assistant_has_marker:
        status = "PASS_FINAL_ASSISTANT_CONTENT"
    elif thinking_has_marker:
        status = "FAIL_MARKER_ONLY_IN_REASONING"
    elif warning:
        status = "FAIL_REASONING_ONLY_LENGTH_WARNING"
    else:
        status = "FAIL_NO_MARKER"
    return {
        "status": status,
        "assistantHasMarker": assistant_has_marker,
        "thinkingHasMarker": thinking_has_marker,
        "warningShown": warning,
        "assistantChars": len(assistant_text),
        "thinkingChars": len(thinking_text),
        "assistantPreview": assistant_text[:1200],
        "thinkingPreview": thinking_text[:1200],
    }


def main() -> None:
    model = Path(os.environ.get("EXPLOITBOT_REASONING_MODEL", str(MODEL_27B))).expanduser()
    output = Path(os.environ.get("EXPLOITBOT_REASONING_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    marker = os.environ.get("EXPLOITBOT_REASONING_MARKER", DEFAULT_MARKER)
    max_tokens = int(os.environ.get("EXPLOITBOT_REASONING_MAX_TOKENS", "512"))
    if not model.is_dir():
        raise AssertionError(f"Qwen model folder is missing: {model}")

    live_batch = load_live_batch_module()
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "real-qwen-reasoning-on",
        "model": str(model),
        "marker": marker,
        "maxTokens": max_tokens,
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    engine: subprocess.Popen[str] | None = None
    app: subprocess.Popen[str] | None = None
    cache_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-reasoning-cache-")
    app_home = tempfile.TemporaryDirectory(prefix="exploitbot-reasoning-home-")
    error: Exception | None = None
    try:
        report["memoryPreflight"] = live_batch.live_batch_memory_preflight(model, 1)
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        build_app_bundle()

        app_env = os.environ.copy()
        app_env["EXPLOITBOT_TESTING"] = "1"
        app_env["HOME"] = app_home.name
        app_env["EXPLOITBOT_DATA_DIR"] = str(Path(app_home.name) / ".exploitbot" / "data")
        app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=app_env)
        wait_for_app()

        port = int(os.environ.get("EXPLOITBOT_REASONING_ENGINE_PORT") or free_port())
        base_url = f"http://127.0.0.1:{port}"
        report["baseUrl"] = base_url
        engine = launch_engine(model, port, Path(cache_tmp.name), max_tokens=max_tokens)
        health = wait_health(base_url, engine)
        cache_before = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)

        app_request("POST", "/engine/mock", base_url, timeout=15.0)
        app_request("POST", "/mode", "manual", timeout=15.0)
        app_request("POST", "/reasoning", "on", timeout=15.0)
        app_request(
            "POST",
            "/qa/apply-app-settings",
            {
                "maxIterations": 1,
                "toolSchemaMaxTools": 0,
                "includeUnavailableToolSchemas": False,
                "forceFinalAnswerAfterToolResults": True,
                "engine": {
                    "modelPath": str(model),
                    "useModelGenerationDefaults": False,
                    "maxTokens": max_tokens,
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
                "chat": {"enableReasoning": True},
            },
            timeout=15.0,
        )
        app_request("POST", "/send", proof_prompt(marker), timeout=15.0)
        messages, state = wait_for_completion()
        cache_after = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)
        outcome = classify(messages, marker)

        report.update(
            {
                "ok": outcome["status"] == "PASS_FINAL_ASSISTANT_CONTENT",
                "status": outcome,
                "health": health,
                "messages": messages,
                "state": state,
                "cacheBefore": cache_before,
                "cacheAfter": cache_after,
                "prompt": proof_prompt(marker),
            }
        )
    except Exception as exc:
        error = exc
        report.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        try:
            report["messages"] = app_request("GET", "/messages", timeout=5.0)
            report["state"] = app_request("GET", "/state", timeout=5.0)
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
        if engine is not None and engine.poll() is None:
            try:
                os.killpg(engine.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                engine.wait(timeout=20)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(engine.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                engine.wait(timeout=10)
        if engine is not None:
            report["engineLogTail"] = read_output_tail(engine)
        cache_tmp.cleanup()
        app_home.cleanup()
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error is not None:
        raise error
    print(f"real-qwen-reasoning-on proof status: {report.get('status', {}).get('status')}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"real-qwen-reasoning-on proof failed: {exc}", flush=True)
        raise SystemExit(1)
