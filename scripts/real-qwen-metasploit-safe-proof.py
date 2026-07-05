#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
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
APP_API = "http://127.0.0.1:9999"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
MODEL_27B = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP")
MODEL_35B = Path("/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP")
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-real-qwen-metasploit-safe-27b.json"
FINAL_MARKER = "REAL_QWEN_METASPLOIT_SAFE_FINAL"


def load_live_batch_module():
    path = ROOT / "scripts" / "prove-live-continuous-batching.py"
    spec = importlib.util.spec_from_file_location("exploitbot_live_batch", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load live batch helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:6000]
        raise AssertionError(message + suffix)


def turboquant_q4_kv_enabled(health: dict[str, Any], cache_after: dict[str, Any]) -> bool:
    effective_cache = ((health.get("effective_config") or {}).get("cache") or {})
    effective_kvq = effective_cache.get("kv_cache_quantization") or {}
    after_kvq = cache_after.get("kv_cache_quantization") or {}
    return (
        effective_kvq.get("enabled") is True
        and str(effective_kvq.get("mode") or "").startswith("turboquant-")
        and after_kvq.get("enabled") is True
        and int(after_kvq.get("bits") or 0) == 4
    )


def ssm_companion_not_quantized(cache_after: dict[str, Any]) -> bool:
    native_cache = cache_after.get("native_cache") or {}
    storage_quant = native_cache.get("attention_kv_storage_quantization") or {}
    return (
        storage_quant.get("enabled") is True
        and storage_quant.get("applies_to") == "attention_kv_layers_only"
        and storage_quant.get("ssm_policy") == "native_companion_state"
        and storage_quant.get("rederive") == "async_clean_prefill_on_miss_or_warm_pass"
    )


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


def request_json(method: str, url: str, body: dict[str, Any] | str | None = None, timeout: float = 15.0):
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def app_request(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 15.0):
    return request_json(method, f"{APP_API}{path}", body, timeout=timeout)


def wait_until(predicate, label: str, timeout: float = 60.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = predicate()
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            last = None
        if last:
            return last
        time.sleep(0.5)
    raise AssertionError(f"timed out waiting for {label}: {last}")


def command_path(name: str) -> str | None:
    found = subprocess.run(["/bin/sh", "-lc", f"command -v {name}"], text=True, capture_output=True)
    path = found.stdout.strip()
    return path or None


def msf_version(path: str) -> str:
    result = subprocess.run([path, "-q", "-x", "version; exit"], text=True, capture_output=True, timeout=45)
    output = result.stdout + result.stderr
    require(result.returncode == 0, "msfconsole version command failed", output)
    match = re.search(r"Framework:\s*([^\n]+)", output)
    return match.group(1).strip() if match else ""


def build_app_bundle() -> None:
    result = subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT)
    require(result.returncode == 0, "build_and_run --build-only failed")
    require(APP_BINARY.exists(), f"app binary missing after build: {APP_BINARY}")


def launch_engine(model: Path, port: int, cache_root: Path) -> subprocess.Popen[str]:
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
        os.environ.get("EXPLOITBOT_REAL_QWEN_METASPLOIT_MAX_TOKENS", "384"),
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
    return subprocess.Popen(
        cmd,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )


def terminate_process_group(proc: subprocess.Popen[str] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=25.0)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=10.0)


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


def wait_for_marker(base_url: str, timeout: float = 240.0):
    deadline = time.time() + timeout
    last = "not-started"
    while time.time() < deadline:
        try:
            messages = app_request("GET", "/messages", timeout=5.0)
            state = app_request("GET", "/state", timeout=5.0)
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            last = f"poll-error {type(exc).__name__}: {exc}"
            time.sleep(0.5)
            continue
        text = json.dumps(messages, sort_keys=True)
        if FINAL_MARKER in text and not state.get("isWorking") and not state.get("isStreaming"):
            return messages
        last = f"working={state.get('isWorking')} streaming={state.get('isStreaming')} messages={len(messages)}"
        time.sleep(0.5)
    snapshot: dict[str, Any] = {"note": last}
    try:
        snapshot["messages"] = app_request("GET", "/messages", timeout=5.0)
        snapshot["state"] = app_request("GET", "/state", timeout=5.0)
        snapshot["cacheStats"] = request_json("GET", f"{base_url}/v1/cache/stats", timeout=8.0)
    except Exception as exc:
        snapshot["captureError"] = f"{type(exc).__name__}: {exc}"
    raise AssertionError(f"timed out waiting for {FINAL_MARKER}", snapshot)


def proof_prompt() -> str:
    call = {"name": "metasploit", "arguments": {"command": "version; exit"}}
    return (
        "Authorized local-only Metasploit version proof. Reasoning is off. "
        "Use exactly one metasploit tool call with command `version; exit`. "
        "Do not use exploit modules, payloads, sessions, shells, network targets, or any external host. "
        f"Emit this exact Qwen XML tool call now:\n<tool_call>{json.dumps(call, separators=(',', ':'))}</tool_call>\n"
        f"After the tool result, answer with exact marker {FINAL_MARKER} and one sentence confirming real msfconsole output was captured."
    )


def main() -> None:
    model = Path(os.environ.get("EXPLOITBOT_REAL_QWEN_METASPLOIT_MODEL", str(MODEL_27B))).expanduser()
    output = Path(os.environ.get("EXPLOITBOT_REAL_QWEN_METASPLOIT_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    if "35b" in str(model).lower() and "EXPLOITBOT_REAL_QWEN_METASPLOIT_OUTPUT" not in os.environ:
        output = ROOT / "docs/live-proofs/2026-07-04-real-qwen-metasploit-safe-35b.json"
    require(model.is_dir(), f"Qwen model folder is missing: {model}")

    live_batch = load_live_batch_module()
    msf_path = command_path("msfconsole")
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "real-qwen-metasploit-safe",
        "model": str(model),
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "msfconsolePath": msf_path,
    }
    app: subprocess.Popen[str] | None = None
    engine: subprocess.Popen[str] | None = None
    app_home = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-metasploit-home-")
    cache_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-metasploit-cache-")
    error: Exception | None = None
    try:
        require(msf_path is not None, "msfconsole is missing from PATH")
        report["directMsfVersion"] = msf_version(msf_path)
        report["memoryPreflight"] = live_batch.live_batch_memory_preflight(model, 1)

        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = app_home.name
        env["EXPLOITBOT_DATA_DIR"] = str(Path(app_home.name) / ".exploitbot" / "data")
        build_app_bundle()
        app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
        wait_until(lambda: app_request("GET", "/state", timeout=1.0), "app test server", timeout=30.0)

        port = int(os.environ.get("EXPLOITBOT_REAL_QWEN_METASPLOIT_ENGINE_PORT") or free_port())
        base_url = f"http://127.0.0.1:{port}"
        report["baseUrl"] = base_url
        engine = launch_engine(model, port, Path(cache_tmp.name))
        health = wait_health(base_url, engine)
        cache_before = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)

        app_request("POST", "/engine/mock", base_url, timeout=15.0)
        app_request("POST", "/mode", "autopilot", timeout=15.0)
        app_request("POST", "/tab", "exploit", timeout=15.0)
        app_request("POST", "/reasoning", "off", timeout=15.0)
        app_request(
            "POST",
            "/qa/apply-app-settings",
            {
                "maxIterations": 4,
                "toolSchemaMaxTools": 64,
                "includeUnavailableToolSchemas": False,
                "forceFinalAnswerAfterToolResults": False,
                "engine": {
                    "modelPath": str(model),
                    "useModelGenerationDefaults": False,
                    "maxTokens": 384,
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
                "chat": {"enableReasoning": False},
            },
            timeout=15.0,
        )
        prompt = proof_prompt()
        catalog = app_request(
            "POST",
            "/qa/tool-catalog",
            {"query": prompt, "tab": "exploit", "maxTools": 64, "includeUnavailable": False},
            timeout=15.0,
        )
        require("metasploit" in (catalog.get("toolNames") or []), "metasploit schema missing before real Qwen turn", catalog)
        report["preflightToolCatalog"] = catalog

        app_request("POST", "/send", prompt, timeout=15.0)
        messages = wait_for_marker(base_url)
        state = app_request("GET", "/state", timeout=10.0)
        results = app_request("GET", "/results", timeout=10.0)
        cache_after = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)

        messages_text = json.dumps(messages, sort_keys=True)
        terminal_text = json.dumps((state.get("terminal") or {}).get("commandTranscripts") or [], sort_keys=True)
        results_text = json.dumps(results, sort_keys=True)
        for marker in ("Tool request: metasploit", "msfconsole", "version; exit", "Framework:", "Console  :", FINAL_MARKER):
            require(marker in messages_text, f"chat transcript missing {marker!r}", messages)
        for marker in ("metasploit", "msfconsole", "version; exit", "Framework:", "Console  :"):
            require(marker in terminal_text, f"terminal commandTranscripts missing {marker!r}", state.get("terminal"))
        for marker in ("Framework:", "Console  :"):
            require(marker in results_text, f"raw results missing {marker!r}", results)

        native_cache = cache_after.get("native_cache") or {}
        scheduler = cache_after.get("scheduler_stats") or {}
        scheduler_cache = cache_after.get("scheduler_cache") or {}
        ssm_rederive = ((cache_after.get("ssm_companion") or {}).get("rederive") or {})
        require(turboquant_q4_kv_enabled(health, cache_after), "TurboQuant q4 KV cache not active", {
            "healthEffectiveCache": ((health.get("effective_config") or {}).get("cache") or {}),
            "cacheAfter": cache_after.get("kv_cache_quantization"),
        })
        require(
            ssm_companion_not_quantized(cache_after),
            "SSM companion state must stay native/rederive-only while attention KV uses TurboQuant",
            native_cache.get("attention_kv_storage_quantization"),
        )
        require(native_cache.get("cache_type") == "hybrid_ssm_typed", "hybrid native cache not active", cache_after)
        require(native_cache.get("paged") is True and int(scheduler_cache.get("block_size") or 0) > 0, "paged cache not active", cache_after)
        require(native_cache.get("prefix") is True and int(scheduler_cache.get("total_tokens_cached") or 0) > 0, "prefix cache not active", cache_after)
        require(int((cache_after.get("block_disk_cache") or {}).get("disk_writes") or 0) >= 1, "block L2 writes missing", cache_after)
        require(int(ssm_rederive.get("failed") or 0) == 0, "SSM rederive failed", cache_after)
        require(int(scheduler.get("num_requests_processed") or 0) >= 2, "model did not process tool and final turns", scheduler)

        report.update(
            {
                "ok": True,
                "health": health,
                "messages": messages,
                "state": state,
                "results": results,
                "cacheBefore": cache_before,
                "cacheAfter": cache_after,
                "chatContainsMetasploitOutput": "Framework:" in messages_text,
                "terminalContainsMetasploitOutput": "Framework:" in terminal_text,
                "resultsContainMetasploitOutput": "Framework:" in results_text,
                "status": {
                    "realQwenDroveRealMetasploit": "PASS",
                    "realMetasploitSafeAppExecution": "PASS",
                    "verboseChatToolOutput": "PASS",
                    "terminalTranscriptOutput": "PASS",
                    "rawResultsOutput": "PASS",
                    "q4TurboQuantKV": "PASS",
                    "q4KV": "PASS",
                    "ssmCompanionNotQuantized": "PASS",
                    "hybridSSM": "PASS",
                    "pagedCache": "PASS",
                    "prefixCache": "PASS",
                    "blockL2": "PASS",
                },
            }
        )
    except Exception as exc:
        error = exc
        report.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        preflight_report = getattr(exc, "report", None)
        if isinstance(preflight_report, dict):
            report["memoryPreflight"] = preflight_report
            report["status"] = {"memoryPreflight": "BLOCKED"}
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
        if engine is not None:
            terminate_process_group(engine)
            report["engineLogTail"] = read_output_tail(engine)
        app_home.cleanup()
        cache_tmp.cleanup()
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error is not None:
        raise error
    print("real-qwen-metasploit-safe proof passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"real-qwen-metasploit-safe proof failed: {exc}", flush=True)
        raise SystemExit(1)
