#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import signal
import socket
import stat
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
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-27b.json"


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


def capture_attempt(base_url: str, attempt: int, status: str, note: str) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "attempt": attempt,
        "status": status,
        "note": note,
        "capturedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    try:
        snapshot["messages"] = app_request("GET", "/messages", timeout=5.0)
    except Exception as exc:
        snapshot["messagesError"] = f"{type(exc).__name__}: {exc}"
    try:
        snapshot["state"] = app_request("GET", "/state", timeout=5.0)
    except Exception as exc:
        snapshot["stateError"] = f"{type(exc).__name__}: {exc}"
    try:
        snapshot["engineHealth"] = request_json("GET", f"{base_url}/health", timeout=8.0)
    except Exception as exc:
        snapshot["engineHealthError"] = f"{type(exc).__name__}: {exc}"
    try:
        snapshot["cacheStats"] = request_json("GET", f"{base_url}/v1/cache/stats", timeout=8.0)
    except Exception as exc:
        snapshot["cacheStatsError"] = f"{type(exc).__name__}: {exc}"
    return snapshot


def wait_for_phase_attempt(base_url: str, attempt: int, timeout: float = 240.0) -> tuple[str, Any]:
    deadline = time.time() + timeout
    last_note = "not-started"
    while time.time() < deadline:
        try:
            messages = app_request("GET", "/messages", timeout=5.0)
            state = app_request("GET", "/state", timeout=5.0)
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            last_note = f"poll-error {type(exc).__name__}: {exc}"
            time.sleep(0.5)
            continue

        has_assistant_marker = any(
            item.get("role") == "assistant" and "REAL_QWEN_PHASE_FINAL" in str(item.get("content") or "")
            for item in messages
        )
        if has_assistant_marker and not state.get("isWorking") and not state.get("isStreaming"):
            return ("success", messages)

        transcripts = ((state.get("terminal") or {}).get("commandTranscripts") or [])
        assistant_messages = [item for item in messages if item.get("role") == "assistant"]
        tool_messages = [
            item for item in messages
            if item.get("role") == "toolCall" or "Tool request:" in str(item.get("content") or "")
        ]
        if (
            not state.get("isWorking")
            and not state.get("isStreaming")
            and assistant_messages
            and not tool_messages
            and not transcripts
        ):
            assistant_text = "\n".join(str(item.get("content") or "") for item in assistant_messages).strip()
            note = "empty assistant/no tool calls" if not assistant_text else "assistant text without tool calls"
            return ("retryable-empty-turn", capture_attempt(base_url, attempt, "retryable-empty-turn", note))

        last_note = f"working={state.get('isWorking')} streaming={state.get('isStreaming')} messages={len(messages)} transcripts={len(transcripts)}"
        time.sleep(0.5)

    return ("timeout", capture_attempt(base_url, attempt, "timeout", last_note))


def build_app_bundle() -> None:
    result = subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError("build_and_run --build-only failed")
    if not APP_BINARY.exists():
        raise RuntimeError(f"app binary missing after build: {APP_BINARY}")


def read_output_tail(proc: subprocess.Popen[str] | None, max_lines: int = 160) -> str:
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


def install_fake_tools(home: Path) -> Path:
    tools_dir = home / ".exploitbot" / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "nmap": "443/tcp open https Apache httpd 2.4.49\n",
        "netexec": "SMB 127.0.0.1 445 QA-SMB [*] Windows Server 2019 signing:false\n",
        "sqlmap": "GET parameter 'id' is vulnerable. injectable boolean-based blind SQL injection\n",
        "hydra": "[22][ssh] host: 127.0.0.1   login: admin   password: Password123!\n",
        "metasploit": "exploit/multi/http/apache_path_traversal\nMeterpreter session 7 opened (127.0.0.1:4444 -> 127.0.0.1:49158)\n",
        "msfconsole": "exploit/multi/http/apache_path_traversal\nMeterpreter session 7 opened (127.0.0.1:4444 -> 127.0.0.1:49158)\n",
        "linpeas.sh": "Hostname: qa-linux-01\nUser: www-data\n",
    }
    for name, output in outputs.items():
        script = tools_dir / name
        script.write_text(f"#!/usr/bin/python3\nimport sys\nsys.stdout.write({output!r})\n", encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return tools_dir


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
        "384",
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
    )


def phase_prompt() -> str:
    return (
        "Authorized loopback-only autonomous phase proof. Reasoning is off. "
        "Use exact Qwen XML tool calls, one for each phase, and no shell commands. "
        "Do not use search_cve, lookup_cve, search_context, or run_shell. "
        "Emit these tool calls now, with valid JSON, then after tool results answer with marker REAL_QWEN_PHASE_FINAL. "
        "Required calls:\n"
        '<tool_call>{"name":"nmap","arguments":{"target":"127.0.0.1","ports":"443","service_detection":true}}</tool_call>\n'
        '<tool_call>{"name":"netexec","arguments":{"target":"127.0.0.1","protocol":"smb","shares":true}}</tool_call>\n'
        '<tool_call>{"name":"sqlmap","arguments":{"url":"http://127.0.0.1/login?id=1","batch":true}}</tool_call>\n'
        '<tool_call>{"name":"hydra","arguments":{"target":"127.0.0.1","protocol":"ssh","username":"admin","password_file":"qa-passwords.txt"}}</tool_call>\n'
        '<tool_call>{"name":"metasploit","arguments":{"module":"exploit/multi/http/apache_path_traversal","target":"127.0.0.1"}}</tool_call>\n'
        '<tool_call>{"name":"linpeas","arguments":{"target":"127.0.0.1"}}</tool_call>'
    )


def main() -> None:
    model = Path(os.environ.get("EXPLOITBOT_REAL_QWEN_PHASE_MODEL", str(MODEL_27B))).expanduser()
    output = Path(os.environ.get("EXPLOITBOT_REAL_QWEN_PHASE_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    if "35b" in str(model).lower() and "EXPLOITBOT_REAL_QWEN_PHASE_OUTPUT" not in os.environ:
        output = ROOT / "docs/live-proofs/2026-07-04-real-qwen-autonomous-phase-35b.json"
    require(model in {MODEL_27B, MODEL_35B} or model.is_dir(), f"Qwen model folder is missing: {model}")

    live_batch = load_live_batch_module()
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "real-qwen-autonomous-phase",
        "model": str(model),
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "phaseAttempts": [],
    }
    error: Exception | None = None
    engine: subprocess.Popen[str] | None = None
    app: subprocess.Popen[str] | None = None
    cache_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-phase-cache-")
    app_home = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-phase-home-")
    try:
        report["memoryPreflight"] = live_batch.live_batch_memory_preflight(model, 1)
        tools_dir = install_fake_tools(Path(app_home.name))
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = app_home.name
        env["EXPLOITBOT_DATA_DIR"] = str(Path(app_home.name) / ".exploitbot" / "data")
        env["PATH"] = f"{tools_dir}:{env.get('PATH', '/usr/bin:/bin')}"
        build_app_bundle()
        app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
        wait_for_app()

        port = int(os.environ.get("EXPLOITBOT_REAL_QWEN_PHASE_ENGINE_PORT") or free_port())
        base_url = f"http://127.0.0.1:{port}"
        report["baseUrl"] = base_url
        engine = launch_engine(model, port, Path(cache_tmp.name))
        health = wait_health(base_url, engine)
        cache_before = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)

        app_request("POST", "/engine/mock", base_url, timeout=15.0)
        app_request("POST", "/mode", "autopilot", timeout=15.0)
        app_request("POST", "/reasoning", "off", timeout=15.0)
        app_request(
            "POST",
            "/qa/apply-app-settings",
            {
                "maxIterations": 8,
                "toolSchemaMaxTools": 64,
                "includeUnavailableToolSchemas": True,
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
        catalog = app_request(
            "POST",
            "/qa/tool-catalog",
            {
                "query": phase_prompt(),
                "tab": "recon",
                "maxTools": 64,
                "includeUnavailable": True,
            },
            timeout=15.0,
        )
        for tool in ("nmap", "netexec", "sqlmap", "hydra", "metasploit", "linpeas"):
            require(tool in (catalog.get("toolNames") or []), f"phase tool schema missing before real Qwen turn: {tool}", catalog)
        report["preflightToolCatalog"] = catalog
        max_attempts = int(os.environ.get("EXPLOITBOT_REAL_QWEN_PHASE_ATTEMPTS", "2"))
        messages: list[dict[str, Any]] | None = None
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                app_request("POST", "/clear", "", timeout=15.0)
                app_request("POST", "/mode", "autopilot", timeout=15.0)
                app_request("POST", "/reasoning", "off", timeout=15.0)
            app_request("POST", "/send", phase_prompt(), timeout=15.0)
            outcome, payload = wait_for_phase_attempt(base_url, attempt, timeout=240.0)
            if outcome == "success":
                messages = payload
                report["phaseAttempts"].append(capture_attempt(base_url, attempt, "success", "final marker reached"))
                break
            report["phaseAttempts"].append(payload)
            if outcome != "retryable-empty-turn" or attempt == max_attempts:
                raise AssertionError(f"real Qwen phase attempt {attempt} failed: {outcome}")
        require(messages is not None, "real Qwen phase final answer missing after attempts", report["phaseAttempts"])
        state = app_request("GET", "/state", timeout=10.0)
        parser_coverage = app_request("GET", "/qa/result-parser-coverage", timeout=10.0)
        results = app_request("GET", "/results", timeout=10.0)
        cache_after = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)
        report["cacheAfter"] = cache_after

        text = json.dumps(messages, sort_keys=True)
        for tool in ("nmap", "netexec", "sqlmap", "hydra", "metasploit", "linpeas"):
            require(tool in text, f"chat transcript missing tool {tool}", messages)
            require(tool in json.dumps(state.get("terminal", {}).get("commandTranscripts", []), sort_keys=True), f"commandTranscripts missing {tool}", state.get("terminal"))

        expected_tabs = {
            "recon": "nmap",
            "network": "netexec",
            "web": "sqlmap",
            "creds": "hydra",
            "exploit": "metasploit",
            "post": "linpeas",
        }
        for tab, tool in expected_tabs.items():
            activity = (state.get("tabActivities") or {}).get(tab) or {}
            require(activity.get("lastTool") == tool and activity.get("status") == "done", f"{tab} activity missing {tool}", activity)

        require(any(port_row.get("port") == 443 and port_row.get("service") == "https" for port_row in results.get("ports", [])), "nmap result missing", results)
        require(any("127.0.0.1 QA-SMB ok" in host for host in parser_coverage.get("networkHosts", [])), "netexec networkHosts missing", parser_coverage)
        result_text = json.dumps(results, sort_keys=True)
        for marker in ("SQL Injection", "Valid Credentials Found", "Session:", "linpeas-host"):
            require(marker in result_text, f"parsed result missing {marker}", results)

        native_cache = cache_after.get("native_cache") or {}
        scheduler = cache_after.get("scheduler_stats") or {}
        scheduler_cache = cache_after.get("scheduler_cache") or {}
        ssm_rederive = ((cache_after.get("ssm_companion") or {}).get("rederive") or {})
        require((cache_after.get("kv_cache_quantization") or {}).get("bits") == 4, "q4 KV cache not active", cache_after)
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
                "parserCoverage": parser_coverage,
                "cacheBefore": cache_before,
                "cacheAfter": cache_after,
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
            engine.send_signal(signal.SIGTERM)
            try:
                engine.wait(timeout=20.0)
            except subprocess.TimeoutExpired:
                engine.kill()
                engine.wait(timeout=10.0)
        if engine is not None:
            report["engineLogTail"] = read_output_tail(engine)
        cache_tmp.cleanup()
        app_home.cleanup()
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if error is not None:
        raise error
    print("real-qwen-autonomous-phase proof passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"real-qwen-autonomous-phase proof failed: {exc}", flush=True)
        raise SystemExit(1)
