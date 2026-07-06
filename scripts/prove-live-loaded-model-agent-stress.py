#!/usr/bin/env python3
from __future__ import annotations

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
APP_API = "http://127.0.0.1:9999"
DEFAULT_MODEL = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP4-CRACK-MTP")
DEFAULT_OUTPUT = ROOT / "docs" / "live-proofs" / "checkpoint-466-qwen-live-agent-stress.json"


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
    raise RuntimeError(f"app test server did not become ready: {last_error}")


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
        time.sleep(0.25)
    raise AssertionError(f"timed out waiting for {label}; last={last_value}")


def int_at(data: dict[str, Any], path: tuple[str, ...]) -> int:
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return 0
        value = value.get(key)
    return int(value or 0) if isinstance(value, (int, float)) else 0


def float_at(data: dict[str, Any], path: tuple[str, ...]) -> float:
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return 0
        value = value.get(key)
    return float(value or 0) if isinstance(value, (int, float)) else 0


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
    model = Path(os.environ.get("EXPLOITBOT_LIVE_AGENT_QWEN_MODEL", str(DEFAULT_MODEL))).expanduser()
    output = Path(os.environ.get("EXPLOITBOT_LIVE_AGENT_STRESS_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    require(model.is_dir(), f"Qwen model folder is missing: {model}")

    port = int(os.environ.get("EXPLOITBOT_LIVE_AGENT_ENGINE_PORT") or free_port())
    base_url = f"http://127.0.0.1:{port}"
    cache_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-live-agent-cache-")
    app_home = tempfile.TemporaryDirectory(prefix="exploitbot-live-agent-home-")
    engine: subprocess.Popen[str] | None = None
    app: subprocess.Popen[str] | None = None
    report: dict[str, Any] = {
        "model": str(model),
        "family": "qwen",
        "baseUrl": base_url,
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "proofType": "live-qwen-loaded-model-agent-stress",
        "agentCount": 2,
        "maxNumSeqs": 2,
    }

    error: Exception | None = None
    try:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = app_home.name
        env["EXPLOITBOT_DATA_DIR"] = str(Path(app_home.name) / ".exploitbot" / "data")
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        engine = launch_engine(model, port, Path(cache_tmp.name))
        health = wait_health(base_url, engine)
        cache_before = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)

        app_request("POST", "/engine/mock", base_url, timeout=15.0)
        app_request(
            "POST",
            "/qa/apply-app-settings",
            {
                "maxIterations": 1,
                "agents": {
                    "multiAgentEnabled": True,
                    "maxConcurrentAgents": 2,
                },
                "chat": {
                    "enableReasoning": False,
                },
                "engine": {
                    "modelPath": str(model),
                    "reasoningParser": "auto",
                    "toolCallParser": "auto",
                    "kvCacheQuantization": "turboquant-q4",
                    "maxTokens": 32,
                    "prefixCache": True,
                    "diskCache": True,
                    "pagedCache": True,
                    "blockDiskCache": True,
                    "cacheMemoryPercent": 0.20,
                },
            },
            timeout=15.0,
        )

        deploy_payloads = [
            {
                "name": "QA Live Qwen Recon",
                "task": "Authorized live Qwen stress lane. Reply with LIVE-AGENT-QWEN-A and one short recon status sentence for 192.0.2.10.",
                "type": "Recon Agent",
            },
            {
                "name": "QA Live Qwen Web",
                "task": "Authorized live Qwen stress lane. Reply with LIVE-AGENT-QWEN-B and one short web status sentence for 192.0.2.10.",
                "type": "Web Vuln Agent",
            },
        ]
        deployed = [app_request("POST", "/qa/deploy-agent", payload, timeout=15.0) for payload in deploy_payloads]
        require(all(item.get("ok") is True for item in deployed), "agent deploy failed", deployed)

        max_working_observed = 0

        def state_with_two_working():
            nonlocal max_working_observed
            state = app_request("GET", "/state", timeout=4.0)
            agents = state.get("agents") or {}
            max_working_observed = max(max_working_observed, int(agents.get("workingCount") or 0))
            return state if int(agents.get("workingCount") or 0) >= 2 else None

        progress = wait_until(state_with_two_working, "two live agents working", timeout=30.0)

        def completed_state():
            nonlocal max_working_observed
            state = app_request("GET", "/state", timeout=4.0)
            agents = state.get("agents") or {}
            max_working_observed = max(max_working_observed, int(agents.get("workingCount") or 0))
            details = agents.get("details") or []
            return state if len(details) >= 2 and all(item.get("isComplete") for item in details) else None

        finished = wait_until(completed_state, "live agents complete", timeout=240.0)
        finished_agents = finished.get("agents") or {}
        finished_details = finished_agents.get("details") or []
        require(max_working_observed >= 2, "app did not expose two live working agents", finished_agents)
        require(len(finished_details) >= 2, "finished state lost live agents", finished_agents)
        require(all(item.get("messageCount", 0) >= 2 for item in finished_details), "live agents did not complete chat turns", finished_details)

        cache_after = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)
        scheduler = cache_after.get("scheduler_stats") or {}
        ssm_companion = cache_after.get("ssm_companion") or {}
        ssm_disk = ssm_companion.get("disk") or {}
        ssm_rederive = ssm_companion.get("rederive") or {}
        ssm_companion_l2_tokens = int_at({"d": ssm_disk}, ("d", "total_tokens_on_disk"))
        require(int_at({"s": scheduler}, ("s", "max_running_observed")) >= 2, "engine did not observe live agent overlap", scheduler)
        require(int_at({"s": scheduler}, ("s", "num_requests_processed")) >= 2, "engine processed too few live agent requests", scheduler)
        require(int_at(cache_after, ("kv_cache_quantization", "bits")) == 4, "live agent KV cache not q4", cache_after)
        require(int_at(cache_after, ("block_disk_cache", "disk_writes")) >= 1, "live agent block L2 writes missing", cache_after)
        require(ssm_companion_l2_tokens >= 1, "live agent SSM companion L2 missing", cache_after)
        require(int_at({"r": ssm_rederive}, ("r", "failed")) == 0, "live agent SSM rederive failed", cache_after)
        require(float_at(cache_after, ("memory", "active_mb")) < 20000, "live agent active memory exceeded low-RAM lane", cache_after)

        report.update(
            {
                "ok": True,
                "health": health,
                "cacheBefore": cache_before,
                "cacheAfter": cache_after,
                "schedulerStats": scheduler,
                "ssmCompanionL2Tokens": ssm_companion_l2_tokens,
                "ssmReDeriveCompleted": int_at({"r": ssm_rederive}, ("r", "completed")),
                "ssmReDeriveFailed": int_at({"r": ssm_rederive}, ("r", "failed")),
                "appProgressSnapshot": progress.get("agents") or {},
                "appFinishedSnapshot": finished_agents,
                "appMaxWorkingObserved": max_working_observed,
                "deployedAgents": deployed,
            }
        )
    except Exception as exc:
        error = exc
        report.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
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
                engine.wait(timeout=15.0)
            except subprocess.TimeoutExpired:
                engine.kill()
                engine.wait(timeout=15.0)
        if engine is not None:
            report["engineLogTail"] = read_output_tail(engine)
        cache_tmp.cleanup()
        app_home.cleanup()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if error is not None:
        raise error
    print("live-loaded-model-agent-stress proof passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"live-loaded-model-agent-stress proof failed: {exc}", flush=True)
        raise SystemExit(1)
