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
DEFAULT_QWEN = Path("/Users/eric/models/JANGQ/Qwen3.6-27B-JANG_4M-MTP")
DEFAULT_OUTPUT = ROOT / "docs" / "live-proofs" / "checkpoint-463-release-app-qwen-cross-restart-cache.json"
PROMPT = "Reply exactly: RELEASE-QWEN-WARM-PASS-OK"


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


def wait_for_engine(timeout: float = 240.0) -> dict[str, Any]:
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


def chat(base_url: str, model_name: str, prompt: str = PROMPT) -> dict[str, Any]:
    return request_json(
        "POST",
        f"{base_url}/v1/chat/completions",
        {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 24,
            "stream": False,
            "enable_thinking": False,
            "chat_template_kwargs": {"enable_thinking": False},
            "stream_options": {"include_usage": True},
        },
        timeout=120.0,
    )


def int_at(data: dict[str, Any], path: tuple[str, ...]) -> int:
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return 0
        value = value.get(key)
    return int(value or 0) if isinstance(value, (int, float)) else 0


def cached_tokens(completion: dict[str, Any]) -> int:
    usage = completion.get("usage") or {}
    details = usage.get("prompt_tokens_details") or {}
    return int_at({"details": details}, ("details", "cached_tokens"))


def completion_text(completion: dict[str, Any]) -> str:
    choices = completion.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content") or message.get("reasoning_content") or "")


def cache_summary(cache: dict[str, Any]) -> dict[str, Any]:
    return {
        "cachedSchedulerHits": int_at(cache, ("scheduler_cache", "hits")),
        "schedulerDiskHits": int_at(cache, ("scheduler_cache", "disk_hits")),
        "schedulerTokensSaved": int_at(cache, ("scheduler_cache", "tokens_saved")),
        "promptL2Hits": int_at(cache, ("disk_cache", "hits")),
        "blockL2DiskHits": int_at(cache, ("block_disk_cache", "disk_hits")),
        "blockL2BlocksOnDisk": int_at(cache, ("block_disk_cache", "blocks_on_disk")),
        "ssmDiskHits": int_at(cache, ("ssm_companion", "disk", "hits")),
        "ssmDiskEntries": int_at(cache, ("ssm_companion", "disk", "entries")),
        "ssmReDeriveRequested": int_at(cache, ("ssm_companion", "rederive", "requested")),
        "ssmReDeriveCompleted": int_at(cache, ("ssm_companion", "rederive", "completed")),
        "ssmReDeriveFailed": int_at(cache, ("ssm_companion", "rederive", "failed")),
    }


def launch_app(home: str) -> subprocess.Popen[bytes]:
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    env = {
        **os.environ,
        "EXPLOITBOT_TESTING": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": home,
    }
    app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
    wait_for_app()
    return app


def stop_app(app: subprocess.Popen[bytes] | None) -> None:
    try:
        app_request("POST", "/engine/stop", timeout=5.0)
    except Exception:
        pass
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if app is not None and app.poll() is None:
        app.send_signal(signal.SIGTERM)
        try:
            app.wait(timeout=5)
        except subprocess.TimeoutExpired:
            app.kill()


def run_phase(home: str, model: Path, phase: str) -> dict[str, Any]:
    app: subprocess.Popen[bytes] | None = None
    report: dict[str, Any] = {"phase": phase}
    try:
        app = launch_app(home)
        runtime = app_request("GET", "/qa/engine-python-runtime")
        selected = runtime.get("selected") or {}
        require(selected.get("source") == "app-bundled-vmlx-python", "release app did not select app-bundled vMLX Python", runtime)
        require(selected.get("missingModuleCount") == 0, "release app bundled Python is missing engine modules", runtime)
        selected_model = app_request("POST", "/qa/model-folder", str(model))
        require(selected_model.get("ok") is True, "model folder selection failed", selected_model)
        started = app_request("POST", "/engine/start")
        require(started.get("ok") is True, "engine start request failed", started)
        state = wait_for_engine()
        port = int(state["enginePort"])
        base_url = f"http://127.0.0.1:{port}"
        health = request_json("GET", f"{base_url}/health", timeout=10.0)
        model_name = health.get("model_name") or model.name
        completion = chat(base_url, model_name)
        cache = request_json("GET", f"{base_url}/v1/cache/stats", timeout=10.0)

        effective = health.get("effective_config") or {}
        cache_config = effective.get("cache") or {}
        topology = cache_config.get("topology") or {}
        kv = cache_config.get("kv_cache_quantization") or {}
        require(topology.get("name") == "hybrid_ssm_attention", "Qwen did not report hybrid SSM attention topology", health)
        require(topology.get("cache_type") == "hybrid", "Qwen did not report hybrid cache type", health)
        require(kv.get("mode") == "turboquant-q4", "Qwen did not enable TurboQuant q4 KV cache", health)
        require((cache_config.get("prefix_cache") or {}).get("enabled") is True, "Qwen prefix cache not enabled", health)
        require((cache_config.get("paged_cache") or {}).get("enabled") is True, "Qwen paged cache not enabled", health)
        require((cache_config.get("ssm_companion") or {}).get("disk_l2_enabled") is True, "Qwen SSM companion L2 not reported", health)
        require(completion_text(completion), f"{phase} completion was empty", completion)

        report.update(
            {
                "runtime": runtime,
                "state": state,
                "health": health,
                "completionPreview": completion_text(completion)[:300],
                "completionUsage": completion.get("usage", {}),
                "cachedTokens": cached_tokens(completion),
                "cacheStats": cache,
                "cacheSummary": cache_summary(cache),
            }
        )
        return report
    finally:
        stop_app(app)


def main() -> None:
    model = Path(os.environ.get("EXPLOITBOT_RELEASE_QWEN_MODEL", str(DEFAULT_QWEN))).expanduser()
    output = Path(os.environ.get("EXPLOITBOT_RELEASE_QWEN_CROSS_RESTART_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    require(APP_BINARY.is_file(), "release app binary is missing; run scripts/release-readiness-proof.py first")
    require(model.is_dir(), f"Qwen model folder is missing: {model}")

    home_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-release-qwen-cross-restart-home-")
    report: dict[str, Any] = {
        "app": str(APP),
        "model": str(model),
        "prompt": PROMPT,
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "home": "temporary-shared-across-two-release-app-launches",
    }
    try:
        populate = run_phase(home_tmp.name, model, "populate")
        replay = run_phase(home_tmp.name, model, "replay")
        populate_summary = populate.get("cacheSummary") or {}
        replay_summary = replay.get("cacheSummary") or {}
        require(populate_summary.get("blockL2BlocksOnDisk", 0) > 0, "populate run did not write block L2 cache", populate_summary)
        require(populate_summary.get("ssmDiskEntries", 0) > 0, "populate run did not write SSM companion L2 cache", populate_summary)
        require(replay.get("cachedTokens", 0) > 0, "replay run did not report cached prompt tokens", replay)
        require(replay_summary.get("blockL2DiskHits", 0) > 0, "replay run did not hit block L2 disk cache", replay_summary)
        require(replay_summary.get("ssmDiskHits", 0) > 0, "replay run did not hit SSM companion L2 cache", replay_summary)
        require(replay_summary.get("ssmReDeriveRequested", 0) == 0, "replay used SSM rederive fallback instead of warm SSM L2 hit", replay_summary)
        require(replay_summary.get("ssmReDeriveFailed", 0) == 0, "SSM rederive reported failures", replay_summary)
        report.update({"ok": True, "populate": populate, "replay": replay})
    finally:
        home_tmp.cleanup()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    signed = subprocess.run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(APP)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    require(signed.returncode == 0, "release app signature failed after cross-restart Qwen run", signed.stdout)
    print("release-app-qwen-cross-restart-cache proof passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"release-app-qwen-cross-restart-cache proof failed: {exc}", flush=True)
        raise SystemExit(1)
