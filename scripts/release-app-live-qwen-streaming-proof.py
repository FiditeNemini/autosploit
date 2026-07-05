#!/usr/bin/env python3
from __future__ import annotations

import http.client
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
RELEASE_QWEN_PROOF = ROOT / "scripts" / "release-app-live-qwen-proof.py"
DEFAULT_QWEN = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP")
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-05-release-app-live-qwen-27b-streaming-current.json"


def load_release_helpers():
    spec = importlib.util.spec_from_file_location("release_app_live_qwen_proof", RELEASE_QWEN_PROOF)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {RELEASE_QWEN_PROOF}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


release = load_release_helpers()


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:4000]
        raise AssertionError(message + suffix)


def stream_chat(base_url: str, model_name: str, prompt: str) -> dict[str, Any]:
    host_port = base_url.removeprefix("http://")
    host, port_text = host_port.rsplit(":", 1)
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 48,
        "stream": True,
        "enable_thinking": True,
        "chat_template_kwargs": {"enable_thinking": True},
        "stream_options": {"include_usage": True},
    }
    conn = http.client.HTTPConnection(host, int(port_text), timeout=180.0)
    data_lines: list[str] = []
    json_frames: list[dict[str, Any]] = []
    raw_preview: list[str] = []
    done_frame_seen = False
    try:
        conn.request(
            "POST",
            "/v1/chat/completions",
            body=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        )
        resp = conn.getresponse()
        require(resp.status == 200, "streaming chat returned non-200 status", {"status": resp.status, "reason": resp.reason})
        while True:
            line = resp.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").strip()
            if not text:
                continue
            if len(raw_preview) < 24:
                raw_preview.append(text[:500])
            if not text.startswith("data:"):
                continue
            value = text.removeprefix("data:").strip()
            data_lines.append(value)
            if value == "[DONE]":
                done_frame_seen = True
                break
            json_frames.append(json.loads(value))
    finally:
        conn.close()

    content_delta_count = 0
    reasoning_delta_count = 0
    tool_call_delta_count = 0
    usage_frame_seen = False
    cached_tokens: int | None = None
    text_preview_parts: list[str] = []
    reasoning_preview_parts: list[str] = []
    for frame in json_frames:
        usage = frame.get("usage")
        if usage is not None:
            usage_frame_seen = True
            details = usage.get("prompt_tokens_details") or {}
            if "cached_tokens" in details:
                cached_tokens = int(details.get("cached_tokens") or 0)
        for choice in frame.get("choices") or []:
            delta = choice.get("delta") or {}
            content = delta.get("content")
            reasoning = delta.get("reasoning_content")
            if content:
                content_delta_count += 1
                text_preview_parts.append(str(content))
            if reasoning:
                reasoning_delta_count += 1
                reasoning_preview_parts.append(str(reasoning))
            if delta.get("tool_calls"):
                tool_call_delta_count += 1

    return {
        "request": payload,
        "rawDataLineCount": len(data_lines),
        "sseJsonFrameCount": len(json_frames),
        "doneFrameSeen": done_frame_seen,
        "contentDeltaCount": content_delta_count,
        "reasoningDeltaCount": reasoning_delta_count,
        "toolCallDeltaCount": tool_call_delta_count,
        "usageFrameSeen": usage_frame_seen,
        "cachedTokens": 0 if cached_tokens is None else cached_tokens,
        "cachedTokensFieldSeen": cached_tokens is not None,
        "textPreview": "".join(text_preview_parts)[:300],
        "reasoningPreview": "".join(reasoning_preview_parts)[:300],
        "rawPreview": raw_preview,
    }


def runtime_status(health: dict[str, Any], stream: dict[str, Any], report: dict[str, Any]) -> dict[str, str]:
    effective = health.get("effective_config") or {}
    cache = effective.get("cache") or {}
    topology = cache.get("topology") or {}
    kv = cache.get("kv_cache_quantization") or {}
    mtp = health.get("mtp") or {}
    return {
        "sseDoneFrame": "PASS" if stream.get("doneFrameSeen") is True else "FAIL",
        "sseJsonFrames": "PASS" if int(stream.get("sseJsonFrameCount") or 0) > 0 else "FAIL",
        "streamContentOrReasoningDelta": "PASS"
        if int(stream.get("contentDeltaCount") or 0) + int(stream.get("reasoningDeltaCount") or 0) > 0
        else "FAIL",
        "streamUsageTelemetry": "PASS"
        if stream.get("usageFrameSeen") is True and stream.get("cachedTokensFieldSeen") is True
        else "FAIL",
        "turboQuantKV": "PASS" if kv.get("mode") == "turboquant-q4" else "FAIL",
        "hybridSSMTopology": "PASS"
        if topology.get("name") == "hybrid_ssm_attention" and topology.get("cache_type") == "hybrid"
        else "FAIL",
        "prefixCache": "PASS" if (cache.get("prefix_cache") or {}).get("enabled") is True else "FAIL",
        "pagedCache": "PASS" if (cache.get("paged_cache") or {}).get("enabled") is True else "FAIL",
        "ssmCompanion": "PASS" if (cache.get("ssm_companion") or {}).get("enabled") is True else "FAIL",
        "nativeD3MTP": "PASS"
        if mtp.get("runtime_active") is True and int(mtp.get("effective_depth") or 0) == 3
        else "FAIL",
        "productionStopClean": "PASS" if report.get("productionStopClean") else "FAIL",
        "postCleanupClean": "PASS" if report.get("postCleanupClean") else "FAIL",
    }


def main() -> None:
    model = Path(os.environ.get("EXPLOITBOT_RELEASE_QWEN_MODEL", str(DEFAULT_QWEN))).expanduser()
    output = Path(os.environ.get("EXPLOITBOT_RELEASE_QWEN_STREAM_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    require(release.APP_BINARY.is_file(), "release app binary is missing; run scripts/release-readiness-proof.py first")
    require(model.is_dir(), f"Qwen model folder is missing: {model}")

    release.terminate_release_engine_processes()
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    home_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-release-qwen-stream-home-")
    env = {**os.environ, "EXPLOITBOT_TESTING": "1", "PYTHONDONTWRITEBYTECODE": "1", "HOME": home_tmp.name}
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "release-app-live-qwen-streaming",
        "app": str(release.APP),
        "model": str(model),
        "startedAt": timestamp(),
    }

    report["memoryPreflight"] = release.wait_for_release_qwen_memory_slot(model)
    app = subprocess.Popen([str(release.APP_BINARY)], cwd=ROOT, env=env)
    try:
        release.wait_for_app()
        runtime = release.app_request("GET", "/qa/engine-python-runtime")
        selected = runtime.get("selected") or {}
        require(selected.get("source") == "app-bundled-vmlx-python", "release app did not select app-bundled vMLX Python", runtime)
        require(selected.get("missingModuleCount") == 0, "release app bundled Python is missing engine modules", runtime)
        report["runtime"] = runtime

        selected_model = release.app_request("POST", "/qa/model-folder", str(model))
        require(selected_model.get("ok") is True, "model folder selection failed", selected_model)
        started = release.app_request("POST", "/engine/start")
        require(started.get("ok") is True, "engine start request failed", started)
        state = release.wait_for_engine()
        port = int(state["enginePort"])
        base_url = f"http://127.0.0.1:{port}"
        health = release.request_json("GET", f"{base_url}/health", timeout=10.0)
        model_name = health.get("model_name") or model.name
        stream = stream_chat(base_url, model_name, "Think briefly, then answer exactly: STREAM-QWEN-OK")

        report.update(
            {
                "state": state,
                "health": health,
                "stream": stream,
            }
        )
    finally:
        try:
            release.app_request("POST", "/engine/stop", timeout=20.0)
        except Exception:
            pass
        production_stop_rows = release.release_engine_process_rows()
        report["productionStopProcessRows"] = production_stop_rows
        report["productionStopClean"] = not production_stop_rows
        if app.poll() is None:
            app.send_signal(15)
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cleanup = release.terminate_release_engine_processes()
        report["cleanupTerminatedProcessRows"] = cleanup["before"]
        report["postCleanupProcessRows"] = cleanup["after"]
        report["postCleanupClean"] = not cleanup["after"]
        home_tmp.cleanup()

    report["generatedAt"] = timestamp()
    report["status"] = runtime_status(report.get("health") or {}, report.get("stream") or {}, report)
    report["ok"] = all(value == "PASS" for value in report["status"].values())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    require(report["ok"] is True, "release app live Qwen streaming proof failed", report)
    signed = subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(release.APP)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    require(signed.returncode == 0, "release app signature failed after live Qwen streaming run", signed.stdout)
    print(f"release-app-live-qwen-streaming proof passed and wrote {output}")


if __name__ == "__main__":
    try:
        with app_proof_lock("release-app-live-qwen-streaming-proof.py"):
            main()
    except Exception as exc:
        print(f"release-app-live-qwen-streaming proof failed: {exc}", flush=True)
        raise SystemExit(1)
