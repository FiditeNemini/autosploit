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
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = ROOT / "ExploitBotEngine"
LAUNCH_PY = ENGINE_DIR / "launch.py"
APP_API = "http://127.0.0.1:9999"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
MODEL_27B = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP")
MODEL_35B = Path("/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP")
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-real-qwen-real-tools-loopback-27b.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


live_batch = load_module("exploitbot_live_batch", ROOT / "scripts" / "prove-live-continuous-batching.py")
installed_tools = load_module("exploitbot_real_installed_tools", ROOT / "scripts" / "real-installed-tools-loopback-proof.py")


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


def build_app_bundle() -> None:
    result = subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError("build_and_run --build-only failed")
    if not APP_BINARY.exists():
        raise RuntimeError(f"app binary missing after build: {APP_BINARY}")


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
        os.environ.get("EXPLOITBOT_REAL_QWEN_REAL_TOOLS_MAX_TOKENS", "768"),
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


def read_output_tail(proc: subprocess.Popen[str] | None, max_lines: int = 200) -> str:
    if proc is None or proc.stdout is None:
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
    try:
        proc.wait(timeout=25.0)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=10.0)


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


def real_tool_prompt(lab_port: int, nuclei_template: Path, hydra_password_file: Path) -> str:
    httpx_url = f"http://127.0.0.1:{lab_port}/httpx"
    nuclei_target = f"http://127.0.0.1:{lab_port}"
    curl_command = f"curl -sS -i 'http://127.0.0.1:{lab_port}/proof?tool=curl'"
    nc_command = (
        "printf 'GET /proof?tool=nc HTTP/1.1\\r\\n"
        f"Host: 127.0.0.1:{lab_port}\\r\\nConnection: close\\r\\n\\r\\n' "
        f"| nc 127.0.0.1 {lab_port}"
    )
    calls = [
        {"name": "nmap", "arguments": {"target": "127.0.0.1", "ports": str(lab_port), "service_detection": True}},
        {"name": "httpx", "arguments": {"targets": httpx_url, "status_code": True, "title": True, "tech_detect": True}},
        {"name": "nuclei", "arguments": {"target": nuclei_target, "templates": str(nuclei_template)}},
        {
            "name": "hydra",
            "arguments": {
                "target": "127.0.0.1",
                "protocol": "http-get",
                "port": lab_port,
                "path": "/protected",
                "username": "admin",
                "password_file": str(hydra_password_file),
            },
        },
        {"name": "netexec", "arguments": {"target": "127.0.0.1", "protocol": "smb", "shares": True, "timeout": 2, "smb_timeout": 2}},
        {"name": "linpeas", "arguments": {"flags": "-q -N -o system_information"}},
        {"name": "run_shell", "arguments": {"command": curl_command}},
        {"name": "run_shell", "arguments": {"command": nc_command}},
    ]
    serialized = "\n".join(f"<tool_call>{json.dumps(call, separators=(',', ':'))}</tool_call>" for call in calls)
    return (
        "Authorized safe lab proof. Reasoning is off. Use only loopback 127.0.0.1 or local host. "
        "Do not use external IPs, domains, exploit payloads, or Metasploit. "
        "Use only these tools: nmap, httpx, nuclei, hydra, netexec, linpeas, run_shell. Never use katana. "
        "Emit these exact Qwen XML tool calls now, with valid JSON. "
        "After tool results, answer with marker REAL_QWEN_REAL_TOOLS_FINAL and summarize the captured real tool outputs.\n"
        f"{serialized}"
    )


def wait_for_final_marker(base_url: str, marker: str, timeout: float = 360.0):
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
        text = json.dumps(messages, sort_keys=True)
        if marker in text and not state.get("isWorking") and not state.get("isStreaming"):
            return messages
        last_note = f"working={state.get('isWorking')} streaming={state.get('isStreaming')} messages={len(messages)}"
        time.sleep(0.5)
    snapshot: dict[str, Any] = {"note": last_note}
    try:
        snapshot["messages"] = app_request("GET", "/messages", timeout=5.0)
        snapshot["state"] = app_request("GET", "/state", timeout=5.0)
        snapshot["cacheStats"] = request_json("GET", f"{base_url}/v1/cache/stats", timeout=8.0)
    except Exception as exc:
        snapshot["captureError"] = f"{type(exc).__name__}: {exc}"
    raise AssertionError(f"timed out waiting for {marker}", snapshot)


def run() -> None:
    model = Path(os.environ.get("EXPLOITBOT_REAL_QWEN_REAL_TOOLS_MODEL", str(MODEL_27B))).expanduser()
    output = Path(os.environ.get("EXPLOITBOT_REAL_QWEN_REAL_TOOLS_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    if "35b" in str(model).lower() and "EXPLOITBOT_REAL_QWEN_REAL_TOOLS_OUTPUT" not in os.environ:
        output = ROOT / "docs/live-proofs/2026-07-04-real-qwen-real-tools-loopback-35b.json"
    require(model.is_dir(), f"Qwen model folder is missing: {model}")

    lab_port = free_port()
    lab = ThreadingHTTPServer(("127.0.0.1", lab_port), installed_tools.LabHandler)
    lab_thread = threading.Thread(target=lab.serve_forever, daemon=True)
    lab_thread.start()

    app: subprocess.Popen[str] | None = None
    engine: subprocess.Popen[str] | None = None
    app_home = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-real-tools-home-")
    cache_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-real-qwen-real-tools-cache-")
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "real-qwen-real-installed-tools-loopback",
        "model": str(model),
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "labUrl": f"http://127.0.0.1:{lab_port}/proof",
        "toolInventory": installed_tools.tool_inventory(),
    }
    error: Exception | None = None
    try:
        report["memoryPreflight"] = live_batch.live_batch_memory_preflight(model, 1)
        if not report["toolInventory"]["requiredRealToolsPresent"]:
            raise AssertionError(f"required loopback tools missing: {report['toolInventory']}")
        missing_optional = [
            tool for tool, present in report["toolInventory"]["optionalLoopbackToolsPresent"].items()
            if not present
        ]
        if missing_optional:
            raise AssertionError(f"optional loopback proof tools missing: {missing_optional}")

        home = Path(app_home.name)
        nuclei_template, hydra_password_file = installed_tools.write_lab_assets(home)
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = str(home)
        env["EXPLOITBOT_DATA_DIR"] = str(home / ".exploitbot" / "data")
        build_app_bundle()
        app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
        wait_until(lambda: app_request("GET", "/state", timeout=1.0), "app test server")

        port = int(os.environ.get("EXPLOITBOT_REAL_QWEN_REAL_TOOLS_ENGINE_PORT") or free_port())
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
                "includeUnavailableToolSchemas": False,
                "forceFinalAnswerAfterToolResults": False,
                "engine": {
                    "modelPath": str(model),
                    "useModelGenerationDefaults": False,
                    "maxTokens": 768,
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
        prompt = real_tool_prompt(lab_port, nuclei_template, hydra_password_file)
        catalog = app_request(
            "POST",
            "/qa/tool-catalog",
            {"query": prompt, "tab": "recon", "maxTools": 64, "includeUnavailable": False},
            timeout=15.0,
        )
        for tool in ("nmap", "httpx", "nuclei", "hydra", "netexec", "linpeas", "run_shell"):
            require(tool in (catalog.get("toolNames") or []), f"tool schema missing before real Qwen real-tool turn: {tool}", catalog)
        require("katana" not in (catalog.get("toolNames") or []), "unavailable katana schema leaked into real Qwen real-tool proof", catalog)
        report["preflightToolCatalog"] = catalog

        app_request("POST", "/send", prompt, timeout=15.0)
        messages = wait_for_final_marker(base_url, "REAL_QWEN_REAL_TOOLS_FINAL")
        state = app_request("GET", "/state", timeout=10.0)
        results = app_request("GET", "/results", timeout=10.0)
        cache_after = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)

        messages_text = json.dumps(messages, sort_keys=True)
        transcript = json.dumps((state.get("terminal") or {}).get("commandTranscripts") or [], sort_keys=True)
        results_text = json.dumps(results, sort_keys=True)
        for marker in (
            "Tool request: nmap",
            "Tool request: httpx",
            "Tool request: nuclei",
            "Tool request: hydra",
            "Tool request: netexec",
            "Tool request: linpeas",
            "Tool request: run_shell",
            "ExploitBot HTTPX Lab",
            "exploitbot-loopback-header",
            "http-get",
            "SMB",
            "MacPEAS-ng",
            "EXPLOITBOT_LOOPBACK_LAB_OK",
            "REAL_QWEN_REAL_TOOLS_FINAL",
        ):
            require(marker in messages_text, f"chat transcript missing {marker!r}", messages)
        for marker in (
            "nmap",
            f"{lab_port}/tcp",
            "httpx",
            "ExploitBot HTTPX Lab",
            "nuclei",
            "exploitbot-loopback-header",
            "hydra",
            "letmein",
            "netexec",
            "SMB",
            "linpeas",
            "MacPEAS-ng",
            "run_shell",
            "EXPLOITBOT_LOOPBACK_LAB_OK",
        ):
            require(marker in transcript, f"terminal commandTranscripts missing {marker!r}", state.get("terminal"))
        for marker in (
            f"{lab_port}/tcp",
            "open",
            "ExploitBot HTTPX Lab",
            "exploitbot-loopback-header",
            "letmein",
            "SMB",
            "MacPEAS-ng",
            "EXPLOITBOT_LOOPBACK_LAB_OK",
        ):
            require(marker in results_text, f"raw results missing {marker!r}", results)

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
                "cacheBefore": cache_before,
                "cacheAfter": cache_after,
                "nmapPath": installed_tools.command_path("nmap"),
                "httpxPath": str(home / ".exploitbot" / "tools" / "httpx"),
                "nucleiPath": installed_tools.command_path("nuclei"),
                "hydraPath": installed_tools.command_path("hydra"),
                "netexecPath": str(home / ".local" / "bin" / "netexec"),
                "linpeasPath": str(home / ".exploitbot" / "tools" / "linpeas.sh"),
                "chatContainsRealToolOutput": "EXPLOITBOT_LOOPBACK_LAB_OK" in messages_text,
                "terminalContainsRealToolOutput": "EXPLOITBOT_LOOPBACK_LAB_OK" in transcript,
                "resultsContainRealToolOutput": "EXPLOITBOT_LOOPBACK_LAB_OK" in results_text,
                "status": {
                    "realQwenDroveRealInstalledTools": "PASS",
                    "realInstalledNmapLoopback": "PASS",
                    "realInstalledHttpxLoopback": "PASS",
                    "realInstalledNucleiLoopback": "PASS",
                    "realInstalledHydraLoopback": "PASS",
                    "realInstalledNetexecLoopback": "PASS",
                    "realInstalledLinpeasLocal": "PASS",
                    "realInstalledCurlNcLoopback": "PASS",
                    "fullPentestToolchainInstalled": "PASS" if not report["toolInventory"]["missingPentestTools"] else "PARTIAL",
                    "missingPentestTools": report["toolInventory"]["missingPentestTools"],
                },
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
        lab.shutdown()
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
    print("real-qwen-real-tools-loopback proof passed")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"real-qwen-real-tools-loopback proof failed: {exc}", flush=True)
        raise SystemExit(1)
