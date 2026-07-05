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
ENGINE_LAUNCH = APP / "Contents" / "Resources" / "ExploitBotEngine" / "launch.py"
APP_API = "http://127.0.0.1:9999"
DEFAULT_QWEN = Path("/Users/eric/models/JANGQ/Qwen3.6-27B-JANG_4M-MTP")
DEFAULT_OUTPUT = ROOT / "docs" / "live-proofs" / "checkpoint-454-release-app-qwen-live.json"
HEAVY_MODEL_MARKERS = (
    "ExploitBotEngine/launch.py",
    "vmlx_engine.server",
    "osaurus-evals run",
    "vllm-mlx",
    "mlx_lm.server",
    "llama-server",
)


class ReleaseQwenMemoryPreflightError(RuntimeError):
    def __init__(self, message: str, report: dict[str, Any]):
        super().__init__(message + "\n" + json.dumps(report, indent=2, sort_keys=True))
        self.report = report


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:4000]
        raise AssertionError(message + suffix)


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


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


def chat(base_url: str, model_name: str, prompt: str) -> dict[str, Any]:
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


def release_engine_process_rows() -> list[dict[str, Any]]:
    output = subprocess.check_output(["/bin/ps", "-axo", "pid=,ppid=,pgid=,rss=,command="], text=True)
    rows: list[dict[str, Any]] = []
    current_pid = os.getpid()
    marker = str(ENGINE_LAUNCH)
    for line in output.splitlines():
        parts = line.split(maxsplit=4)
        if len(parts) != 5:
            continue
        pid_text, ppid_text, pgid_text, rss_text, command = parts
        if marker not in command:
            continue
        pid = int(pid_text)
        if pid == current_pid:
            continue
        rows.append(
            {
                "pid": pid,
                "ppid": int(ppid_text),
                "pgid": int(pgid_text),
                "rssKB": int(rss_text),
                "command": command[:800],
            }
        )
    return rows


def terminate_release_engine_processes() -> dict[str, Any]:
    before = release_engine_process_rows()
    for row in before:
        try:
            os.killpg(int(row["pgid"]), signal.SIGTERM)
        except ProcessLookupError:
            pass
        except Exception:
            try:
                os.kill(int(row["pid"]), signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.time() + 5.0
    after_term = release_engine_process_rows()
    while after_term and time.time() < deadline:
        time.sleep(0.25)
        after_term = release_engine_process_rows()
    for row in after_term:
        try:
            os.killpg(int(row["pgid"]), signal.SIGKILL)
        except ProcessLookupError:
            pass
        except Exception:
            try:
                os.kill(int(row["pid"]), signal.SIGKILL)
            except ProcessLookupError:
                pass
    deadline = time.time() + 5.0
    after = release_engine_process_rows()
    while after and time.time() < deadline:
        time.sleep(0.25)
        after = release_engine_process_rows()
    return {"before": before, "afterTerm": after_term, "after": after}


def assert_no_release_engine_processes(rows: list[dict[str, Any]]) -> None:
    require(not rows, "release bundled engine launcher still running after cleanup", rows)


def assert_production_stop_clean(rows: list[dict[str, Any]]) -> None:
    require(not rows, "release app stop left bundled engine launcher running before harness cleanup", rows)


def parse_vm_stat_available_gb(text: str) -> float | None:
    page_size_match = None
    for line in text.splitlines():
        if "page size of" in line:
            page_size_match = line
            break
    if page_size_match is None:
        return None
    digits = "".join(ch for ch in page_size_match if ch.isdigit())
    if not digits:
        return None
    page_size = int(digits)
    wanted = {"Pages free", "Pages inactive", "Pages speculative"}
    pages = 0
    for line in text.splitlines():
        name, sep, raw_value = line.partition(":")
        if sep and name.strip() in wanted:
            pages += int("".join(ch for ch in raw_value if ch.isdigit()) or "0")
    return round((pages * page_size) / (1024 ** 3), 2)


def current_available_memory_gb() -> float | None:
    try:
        output = subprocess.check_output(["/usr/bin/vm_stat"], text=True)
    except Exception:
        return None
    return parse_vm_stat_available_gb(output)


def current_heavy_model_processes() -> list[dict[str, Any]]:
    try:
        output = subprocess.check_output(["/bin/ps", "-axo", "pid=,ppid=,rss=,command="], text=True)
    except Exception:
        return []
    rows: list[dict[str, Any]] = []
    current_pid = os.getpid()
    for line in output.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) != 4 or not parts[0].isdigit():
            continue
        pid = int(parts[0])
        if pid == current_pid:
            continue
        rss_kb = int(parts[2]) if parts[2].isdigit() else 0
        command = parts[3]
        rss_mb = rss_kb / 1024
        is_light_shell_wrapper = (
            rss_mb < 128
            and command.startswith(("/bin/zsh -c", "/bin/sh -c", "zsh -c", "sh -c", "ssh "))
        )
        if is_light_shell_wrapper:
            continue
        if any(marker in command for marker in HEAVY_MODEL_MARKERS):
            rows.append(
                {
                    "pid": pid,
                    "ppid": int(parts[1]) if parts[1].isdigit() else 0,
                    "rssMB": round(rss_mb, 1),
                    "command": command[:500],
                }
            )
    return rows


def required_available_memory_gb(model: Path) -> float:
    override = os.environ.get("EXPLOITBOT_RELEASE_QWEN_MIN_AVAILABLE_GB")
    if override:
        return float(override)
    name = str(model).lower()
    if "35b" in name:
        return 50.0
    if "27b" in name:
        return 42.0
    return 42.0


def release_qwen_memory_preflight(model: Path) -> dict[str, Any]:
    if os.environ.get("EXPLOITBOT_RELEASE_QWEN_SKIP_MEMORY_GUARD") == "1":
        return {
            "enabled": False,
            "skippedBy": "EXPLOITBOT_RELEASE_QWEN_SKIP_MEMORY_GUARD",
        }
    available_gb = current_available_memory_gb()
    required_gb = required_available_memory_gb(model)
    heavy_processes = current_heavy_model_processes()
    allow_concurrent = os.environ.get("EXPLOITBOT_RELEASE_QWEN_ALLOW_CONCURRENT_MODEL") == "1"
    report = {
        "enabled": True,
        "availableGB": available_gb,
        "requiredAvailableGB": required_gb,
        "heavyModelProcessCount": len(heavy_processes),
        "heavyModelProcesses": heavy_processes[:8],
        "allowConcurrentModel": allow_concurrent,
    }
    if heavy_processes and not allow_concurrent:
        raise ReleaseQwenMemoryPreflightError(
            "release Qwen proof refused to stack on another heavyweight model/eval process",
            report,
        )
    if available_gb is not None and available_gb < required_gb:
        raise ReleaseQwenMemoryPreflightError(
            "release Qwen proof refused to start with insufficient available memory",
            report,
        )
    return report


def wait_for_release_qwen_memory_slot(model: Path) -> dict[str, Any]:
    wait_seconds = float(os.environ.get("EXPLOITBOT_RELEASE_QWEN_WAIT_FOR_MEMORY_SLOT_SECONDS", "0") or "0")
    poll_seconds = float(os.environ.get("EXPLOITBOT_RELEASE_QWEN_WAIT_POLL_SECONDS", "5") or "5")
    started = time.time()
    attempts = 0
    last_blocked: dict[str, Any] | None = None
    while True:
        attempts += 1
        try:
            report = release_qwen_memory_preflight(model)
            report["waitForMemorySlot"] = {
                "enabled": wait_seconds > 0,
                "waitSeconds": wait_seconds,
                "pollSeconds": poll_seconds,
                "attempts": attempts,
                "elapsedSeconds": round(time.time() - started, 2),
                "lastBlockedPreflight": last_blocked,
            }
            return report
        except ReleaseQwenMemoryPreflightError as exc:
            last_blocked = exc.report
            elapsed = time.time() - started
            if wait_seconds <= 0 or elapsed >= wait_seconds:
                exc.report["waitForMemorySlot"] = {
                    "enabled": wait_seconds > 0,
                    "waitSeconds": wait_seconds,
                    "pollSeconds": poll_seconds,
                    "attempts": attempts,
                    "elapsedSeconds": round(elapsed, 2),
                    "timedOut": wait_seconds > 0,
                }
                raise
            time.sleep(max(0.5, poll_seconds))


def main() -> None:
    model = Path(os.environ.get("EXPLOITBOT_RELEASE_QWEN_MODEL", str(DEFAULT_QWEN))).expanduser()
    output = Path(os.environ.get("EXPLOITBOT_RELEASE_QWEN_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    require(APP_BINARY.is_file(), "release app binary is missing; run scripts/release-readiness-proof.py first")
    require(model.is_dir(), f"Qwen model folder is missing: {model}")

    terminate_release_engine_processes()
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    home_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-release-qwen-home-")
    env = {**os.environ, "EXPLOITBOT_TESTING": "1", "PYTHONDONTWRITEBYTECODE": "1", "HOME": home_tmp.name}

    report: dict[str, Any] = {
        "app": str(APP),
        "model": str(model),
        "startedAt": timestamp(),
    }
    report["memoryPreflight"] = wait_for_release_qwen_memory_slot(model)
    app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
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
        first = chat(base_url, model_name, "Reply exactly: RELEASE-QWEN-OK")
        cache_after_first = request_json("GET", f"{base_url}/v1/cache/stats", timeout=10.0)
        second = chat(base_url, model_name, "Reply exactly: RELEASE-QWEN-OK")
        cache_after_second = request_json("GET", f"{base_url}/v1/cache/stats", timeout=10.0)

        effective = health.get("effective_config") or {}
        cache = effective.get("cache") or {}
        topology = cache.get("topology") or {}
        kv = cache.get("kv_cache_quantization") or {}
        mtp = health.get("mtp") or {}
        require(topology.get("name") == "hybrid_ssm_attention", "release Qwen did not report hybrid SSM attention topology", health)
        require(topology.get("cache_type") == "hybrid", "release Qwen did not report hybrid cache type", health)
        require(kv.get("mode") == "turboquant-q4", "release Qwen did not enable TurboQuant q4 KV cache", health)
        require((cache.get("prefix_cache") or {}).get("enabled") is True, "release Qwen prefix cache not enabled", health)
        require((cache.get("paged_cache") or {}).get("enabled") is True, "release Qwen paged cache not enabled", health)
        require((cache.get("ssm_companion") or {}).get("enabled") is True, "release Qwen SSM companion cache not enabled", health)
        require(mtp.get("runtime_active") is True, "release Qwen native MTP runtime not active", health)
        require(int(mtp.get("effective_depth") or 0) == 3, "release Qwen native MTP effective depth is not 3", health)
        require(completion_text(first), "release Qwen first chat completion was empty", first)
        require(completion_text(second), "release Qwen second chat completion was empty", second)

        cache_checks = {
            "secondCachedTokens": cached_tokens(second),
            "schedulerHitsDelta": int(((cache_after_second.get("scheduler_cache") or {}).get("hits") or 0)) - int(((cache_after_first.get("scheduler_cache") or {}).get("hits") or 0)),
            "schedulerCacheHitsDelta": int(((cache_after_second.get("scheduler_cache") or {}).get("cache_hits") or 0)) - int(((cache_after_first.get("scheduler_cache") or {}).get("cache_hits") or 0)),
            "ssmDiskHits": int((((cache_after_second.get("ssm_companion") or {}).get("disk") or {}).get("hits") or 0)),
        }
        require(any(value > 0 for value in cache_checks.values()), "release Qwen repeat prompt did not show cache reuse", cache_checks)

        report.update(
            {
                "ok": True,
                "state": state,
                "health": health,
                "firstCompletionPreview": completion_text(first)[:300],
                "firstUsage": first.get("usage", {}),
                "secondCompletionPreview": completion_text(second)[:300],
                "secondUsage": second.get("usage", {}),
                "cacheChecks": cache_checks,
                "cacheAfterFirst": cache_after_first,
                "cacheAfterSecond": cache_after_second,
            }
        )
    finally:
        try:
            app_request("POST", "/engine/stop", timeout=20.0)
        except Exception:
            pass
        production_stop_rows = release_engine_process_rows()
        report["productionStopProcessRows"] = production_stop_rows
        report["productionStopClean"] = not production_stop_rows
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cleanup = terminate_release_engine_processes()
        report["cleanupTerminatedProcessRows"] = cleanup["before"]
        report["postCleanupProcessRows"] = cleanup["after"]
        report["postCleanupClean"] = not cleanup["after"]
        home_tmp.cleanup()

    output.parent.mkdir(parents=True, exist_ok=True)
    report.update(
        {
            "generatedAt": timestamp(),
            "status": {
                "memoryPreflight": "PASS",
                "appBundledRuntime": "PASS",
                "turboQuantKV": "PASS",
                "hybridSSMTopology": "PASS",
                "prefixCache": "PASS",
                "pagedCache": "PASS",
                "ssmCompanion": "PASS",
                "nativeD3MTP": "PASS",
                "repeatPromptCacheReuse": "PASS",
                "productionStopClean": "PASS" if report.get("productionStopClean") else "FAIL",
                "postCleanupClean": "PASS" if report.get("postCleanupClean") else "FAIL",
            },
        }
    )
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert_production_stop_clean(report.get("productionStopProcessRows") or [])
    assert_no_release_engine_processes(report.get("postCleanupProcessRows") or [])
    signed = subprocess.run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(APP)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    require(signed.returncode == 0, "release app signature failed after live Qwen run", signed.stdout)
    print("release-app-live-qwen proof passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"release-app-live-qwen proof failed: {exc}", flush=True)
        raise SystemExit(1)
