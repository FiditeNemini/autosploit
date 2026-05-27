#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "release" / "ExploitBot.app"
APP_BINARY = APP / "Contents" / "MacOS" / "ExploitBot"
APP_API = "http://127.0.0.1:9999"
DEFAULT_MINIMAX = Path("/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ")
DEFAULT_OUTPUT = ROOT / "docs" / "live-proofs" / "checkpoint-459-release-app-minimax-live.json"


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:4000]
        raise AssertionError(message + suffix)


def request_json(method: str, url: str, body: dict[str, Any] | str | None = None, timeout: float = 10.0) -> dict[str, Any]:
    if isinstance(body, str):
        data = body.encode("utf-8")
    elif body is None:
        data = None
    else:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def app_request(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 10.0) -> dict[str, Any]:
    return request_json(method, f"{APP_API}{path}", body, timeout=timeout)


def wait_for_app(timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            app_request("GET", "/state", timeout=1.0)
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"release app test server did not become ready: {last_error}")


def wait_for_engine(timeout: float = 420.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_state: dict[str, Any] = {}
    while time.time() < deadline:
        state = app_request("GET", "/state", timeout=2.0)
        last_state = state
        if state.get("engineRunning") is True and int(state.get("enginePort") or 0) > 0:
            return state
        if state.get("healthStatus") in {"error", "blocked"}:
            raise RuntimeError(f"engine entered {state.get('healthStatus')}: {state.get('engineError')}")
        time.sleep(1.0)
    raise RuntimeError(f"engine did not start before timeout: {last_state}")


def chat(base_url: str, model_name: str, prompt: str, *, enable_thinking: bool) -> dict[str, Any]:
    return request_json(
        "POST",
        f"{base_url}/v1/chat/completions",
        {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 24,
            "stream": False,
            "enable_thinking": enable_thinking,
            "chat_template_kwargs": {"enable_thinking": enable_thinking},
            "stream_options": {"include_usage": True},
        },
        timeout=180.0,
    )


def cached_tokens(completion: dict[str, Any]) -> int:
    usage = completion.get("usage") or {}
    details = usage.get("prompt_tokens_details") or {}
    return int(details.get("cached_tokens") or 0)


def completion_text(completion: dict[str, Any]) -> str:
    choices = completion.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content") or message.get("reasoning_content") or "")


def main() -> None:
    model = Path(os.environ.get("EXPLOITBOT_RELEASE_MINIMAX_MODEL", str(DEFAULT_MINIMAX))).expanduser()
    output = Path(os.environ.get("EXPLOITBOT_RELEASE_MINIMAX_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    require(APP_BINARY.is_file(), "release app binary is missing; run scripts/release-readiness-proof.py first")
    require(model.is_dir(), f"MiniMax model folder is missing: {model}")

    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    home_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-release-minimax-home-")
    env = {**os.environ, "EXPLOITBOT_TESTING": "1", "PYTHONDONTWRITEBYTECODE": "1", "HOME": home_tmp.name}
    app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)

    report: dict[str, Any] = {
        "app": str(APP),
        "model": str(model),
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    try:
        wait_for_app()
        runtime = app_request("GET", "/qa/engine-python-runtime")
        selected = runtime.get("selected") or {}
        require(selected.get("source") == "app-bundled-vmlx-python", "release app did not select app-bundled vMLX Python", runtime)
        require(selected.get("missingModuleCount") == 0, "release app bundled Python is missing engine modules", runtime)
        report["runtime"] = runtime

        selected_model = app_request("POST", "/qa/model-folder", str(model))
        require(selected_model.get("ok") is True, "model folder selection failed", selected_model)
        started = app_request("POST", "/engine/start")
        require(started.get("ok") is True, "engine start request failed", started)
        state = wait_for_engine()
        port = int(state["enginePort"])
        base_url = f"http://127.0.0.1:{port}"
        health = request_json("GET", f"{base_url}/health", timeout=10.0)
        model_name = health.get("model_name") or model.name

        first = chat(base_url, model_name, "ExploitBot MiniMax release no-thinking smoke. Reply briefly.", enable_thinking=False)
        cache_after_first = request_json("GET", f"{base_url}/v1/cache/stats", timeout=10.0)
        second = chat(base_url, model_name, "ExploitBot MiniMax release no-thinking smoke. Reply briefly.", enable_thinking=False)
        cache_after_second = request_json("GET", f"{base_url}/v1/cache/stats", timeout=10.0)
        thinking = chat(base_url, model_name, "ExploitBot MiniMax reasoning toggle smoke. Think if enabled, then answer briefly.", enable_thinking=True)

        effective = health.get("effective_config") or {}
        cache = effective.get("cache") or {}
        topology = cache.get("topology") or {}
        kv = cache.get("kv_cache_quantization") or {}
        parsers = effective.get("parsers") or {}
        require(topology.get("name") == "full_kv_attention", "MiniMax did not report full-KV attention topology", health)
        require(topology.get("cache_type") == "kv", "MiniMax did not report kv cache type", health)
        require(topology.get("ssm_companion_required") is False, "MiniMax should not require SSM companion cache", health)
        require(kv.get("mode") == "turboquant-q4", "MiniMax did not enable TurboQuant q4 KV cache", health)
        require((cache.get("prefix_cache") or {}).get("enabled") is True, "MiniMax prefix cache not enabled", health)
        require((cache.get("paged_cache") or {}).get("enabled") is True, "MiniMax paged cache not enabled", health)
        require(parsers.get("reasoning") == "minimax_m2", "MiniMax reasoning parser was not selected", health)
        require(parsers.get("tool_call") == "minimax", "MiniMax tool parser was not selected", health)
        require(completion_text(first), "MiniMax first no-thinking chat completion was empty", first)
        require(completion_text(second), "MiniMax second no-thinking chat completion was empty", second)
        require(completion_text(thinking), "MiniMax thinking-enabled chat completion was empty", thinking)

        cache_checks = {
            "secondCachedTokens": cached_tokens(second),
            "schedulerHitsDelta": int(((cache_after_second.get("scheduler_cache") or {}).get("hits") or 0)) - int(((cache_after_first.get("scheduler_cache") or {}).get("hits") or 0)),
            "schedulerCacheHitsDelta": int(((cache_after_second.get("scheduler_cache") or {}).get("cache_hits") or 0)) - int(((cache_after_first.get("scheduler_cache") or {}).get("cache_hits") or 0)),
            "schedulerTokensSavedDelta": int(((cache_after_second.get("scheduler_cache") or {}).get("tokens_saved") or 0)) - int(((cache_after_first.get("scheduler_cache") or {}).get("tokens_saved") or 0)),
        }
        require(any(value > 0 for value in cache_checks.values()), "MiniMax repeat prompt did not show cache reuse", cache_checks)

        report.update(
            {
                "ok": True,
                "state": state,
                "health": health,
                "firstNoThinkingPreview": completion_text(first)[:300],
                "firstNoThinkingUsage": first.get("usage", {}),
                "secondNoThinkingPreview": completion_text(second)[:300],
                "secondNoThinkingUsage": second.get("usage", {}),
                "thinkingPreview": completion_text(thinking)[:300],
                "thinkingUsage": thinking.get("usage", {}),
                "cacheChecks": cache_checks,
                "cacheAfterFirst": cache_after_first,
                "cacheAfterSecond": cache_after_second,
            }
        )
    finally:
        try:
            app_request("POST", "/engine/stop", timeout=5.0)
        except Exception:
            pass
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)
        home_tmp.cleanup()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    signed = subprocess.run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(APP)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    require(signed.returncode == 0, "release app signature failed after live MiniMax run", signed.stdout)
    print("release-app-live-minimax proof passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"release-app-live-minimax proof failed: {exc}", flush=True)
        raise SystemExit(1)
