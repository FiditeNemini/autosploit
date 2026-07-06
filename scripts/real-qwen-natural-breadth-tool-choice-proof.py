#!/usr/bin/env python3

import importlib.util
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = ROOT / "ExploitBotEngine"
LAUNCH_PY = ENGINE_DIR / "launch.py"
MODEL_27B = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP4-CRACK-MTP")
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-06-real-qwen-natural-breadth-tool-choice-27b.json"


@dataclass(frozen=True)
class BreadthScenario:
    scenario_id: str
    category: str
    prompt: str
    expected_tool: str
    safety_boundary: str = "local_fixture_or_synthetic_objective_only"


SCENARIOS = [
    BreadthScenario(
        "subdomain_recon",
        "recon",
        "Authorized synthetic engagement. The target owner asks for subdomain discovery for example.test before any probing. Choose the best first tool.",
        "subfinder",
    ),
    BreadthScenario(
        "network_service_enum",
        "network",
        "Authorized loopback lab. Determine which TCP services are exposed on 127.0.0.1 before any web probing. Choose the best first tool.",
        "nmap",
    ),
    BreadthScenario(
        "wordpress_web_risk",
        "web",
        "Authorized local WordPress fixture. Identify plugins/themes and known WordPress risks before exploitation. Choose the best first tool.",
        "wpscan",
    ),
    BreadthScenario(
        "ssh_credential_validation",
        "creds",
        "Authorized credential audit against a local SSH lab with a supplied tiny password list. Validate seeded credentials only. Choose the best first tool.",
        "hydra",
    ),
    BreadthScenario(
        "container_supply_chain",
        "supply",
        "Authorized local container/IaC repo. Build an SBOM before vulnerability matching or policy checks. Choose the best first tool.",
        "syft",
    ),
    BreadthScenario(
        "web_template_vuln",
        "web",
        "Authorized loopback web fixture. Run safe template-based checks for exposed known web issues after discovery. Choose the best first tool.",
        "nuclei",
    ),
    BreadthScenario(
        "secret_discovery",
        "supply",
        "Authorized throwaway git repository. Find accidental secrets before dependency analysis. Choose the best first tool.",
        "trufflehog",
    ),
    BreadthScenario(
        "osint_username",
        "osint",
        "Authorized OSINT training fixture. Check whether the username alice-example appears across public profile sites. Choose the best first tool.",
        "sherlock",
    ),
    BreadthScenario(
        "ssrf_web_probe",
        "web",
        "Authorized local SSRF lab. First confirm the loopback HTTP surface and title before running templates. Choose the best first tool.",
        "httpx",
    ),
    BreadthScenario(
        "iac_policy_check",
        "supply",
        "Authorized local Kubernetes manifest review. Detect risky securityContext policy such as allowPrivilegeEscalation. Choose the best first tool.",
        "checkov",
    ),
]


TOOLS: dict[str, str] = {
    "subfinder": "Discover subdomains for an in-scope domain.",
    "nmap": "Enumerate open TCP ports and service banners on an in-scope host.",
    "wpscan": "Inspect WordPress core, plugin, theme, and user exposure.",
    "hydra": "Validate supplied credentials against an authorized service.",
    "syft": "Generate a software bill of materials for a local image or filesystem.",
    "nuclei": "Run safe vulnerability templates against an in-scope web target.",
    "trufflehog": "Scan a local repository for accidental secret exposure.",
    "sherlock": "Search public profile sites for an authorized username.",
    "httpx": "Probe HTTP services, status, titles, and technologies.",
    "checkov": "Scan local IaC files for policy violations.",
    "sqlmap": "Validate SQL injection only against authorized web parameters.",
    "search_cve": "Search the local CVE context library for vulnerability enrichment.",
}


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


live_batch = load_module("exploitbot_live_batch_for_natural_breadth", ROOT / "scripts" / "prove-live-continuous-batching.py")


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


def request_json(method: str, url: str, body: dict[str, Any] | None = None, timeout: float = 30.0) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_health(base_url: str, proc: subprocess.Popen[str], timeout: float = 420.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_error: Any = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"engine exited before health: exit={proc.returncode}\n{read_output_tail(proc)}")
        try:
            health = request_json("GET", f"{base_url}/health", timeout=8.0)
            if health.get("status") == "healthy":
                return health
            last_error = health
        except Exception as exc:
            last_error = exc
        time.sleep(1.0)
    raise RuntimeError(f"engine did not become healthy: {last_error}")


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
        "128",
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
    cache_root.mkdir(parents=True, exist_ok=True)
    log_path = cache_root / "engine.log"
    log_file = log_path.open("w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
    except BaseException:
        log_file.close()
        raise
    log_file.close()
    proc.exploitbot_log_path = log_path  # type: ignore[attr-defined]
    return proc


def terminate_process_group(proc: subprocess.Popen[str] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception:
        proc.terminate()
    try:
        proc.wait(timeout=15.0)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except Exception:
            proc.kill()
        proc.wait(timeout=5.0)


def read_output_tail(proc: subprocess.Popen[str] | None, max_lines: int = 180) -> str:
    if proc is None:
        return ""
    log_path = getattr(proc, "exploitbot_log_path", None)
    if log_path is None:
        return ""
    try:
        text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"<unable to read process log {log_path}: {exc}>"
    return "\n".join(text.splitlines()[-max_lines:])


def tool_schema(name: str, description: str) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Authorized local fixture or synthetic target."},
                    "reason": {"type": "string", "description": "Brief reason for choosing this tool."},
                },
                "required": ["target"],
            },
        },
    }


def all_tool_schemas() -> list[dict[str, Any]]:
    return [tool_schema(name, description) for name, description in TOOLS.items()]


def prompt_has_tool_blocks(text: str) -> bool:
    return "<tool_call>" in text or "</tool_call>" in text


def selected_tool(response: dict[str, Any]) -> str | None:
    choices = response.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}
    calls = message.get("tool_calls") or []
    if calls:
        function = calls[0].get("function") or {}
        name = function.get("name")
        return str(name) if name else None
    content = str(message.get("content") or "")
    if "<tool_call>" in content:
        try:
            payload = content.split("<tool_call>", 1)[1].split("</tool_call>", 1)[0]
            parsed = json.loads(payload)
            name = parsed.get("name")
            return str(name) if name else None
        except Exception:
            return None
    return None


def run_scenario(base_url: str, model: Path, scenario: BreadthScenario) -> dict[str, Any]:
    system = (
        "You are ExploitBot's authorized local-lab planning model. "
        "Choose exactly one best first tool from the provided tool schemas. "
        "Call the tool; do not answer in prose. Stay inside the stated local/synthetic scope."
    )
    body = {
        "model": str(model),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": scenario.prompt},
        ],
        "tools": all_tool_schemas(),
        "tool_choice": "auto",
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 128,
        "stream": False,
        "enable_thinking": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    started = time.time()
    response = request_json("POST", f"{base_url}/v1/chat/completions", body, timeout=120.0)
    elapsed = round(time.time() - started, 3)
    choice = selected_tool(response)
    return {
        "scenarioId": scenario.scenario_id,
        "category": scenario.category,
        "expectedTool": scenario.expected_tool,
        "selectedTool": choice,
        "status": "PASS" if choice == scenario.expected_tool else "FAIL",
        "latencySeconds": elapsed,
        "promptExactToolCallBlocksPresent": prompt_has_tool_blocks(scenario.prompt),
        "safetyBoundary": scenario.safety_boundary,
        "finishReason": ((response.get("choices") or [{}])[0] or {}).get("finish_reason"),
        "responseId": response.get("id"),
        "usage": response.get("usage") or {},
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def output_path_for_model(model: Path) -> Path:
    override = os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_BREADTH_OUTPUT")
    if override:
        return Path(override).expanduser()
    return DEFAULT_OUTPUT


def cache_status(cache: dict[str, Any]) -> dict[str, str]:
    kvq = cache.get("kv_cache_quantization") or {}
    native = cache.get("native_cache") or {}
    block = cache.get("block_disk_cache") or {}
    last_mtp = (((cache.get("scheduler_stats") or {}).get("batch_generator") or {}).get("last_native_mtp") or {})
    drafted_by_depth = last_mtp.get("drafted_by_depth") or []
    d3_drafted = len(drafted_by_depth) >= 3 and drafted_by_depth[2] > 0
    return {
        "q4TurboQuantKV": "PASS" if kvq.get("enabled") is True and int(kvq.get("bits") or 0) == 4 else "FAIL",
        "prefixCache": "PASS" if native.get("prefix") is True else "FAIL",
        "pagedCache": "PASS" if native.get("paged") is True else "FAIL",
        "blockDiskCache": "PASS" if block.get("disk_writes", 0) >= 0 and native.get("block_disk_l2") is True else "FAIL",
        "nativeMTPD3": "PASS" if d3_drafted and (last_mtp.get("forwards") or {}).get("mtp", 0) > 0 else "FAIL",
    }


def run() -> None:
    model = Path(os.environ.get("EXPLOITBOT_REAL_QWEN_NATURAL_BREADTH_MODEL", str(MODEL_27B))).expanduser()
    output = output_path_for_model(model)
    started_at = timestamp()
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "real-qwen-natural-breadth-tool-choice",
        "proofLevel": "direct-engine-real-qwen-natural-language-tool-selection",
        "toolChoiceMode": "model_selected_tool_sequence",
        "modelToolChoiceEvidence": "model_selected_tool_sequence",
        "appLoopEvidence": "not_claimed",
        "safeBoundary": "local_fixture_or_synthetic_objective_only",
        "model": str(model),
        "startedAt": started_at,
        "scenarioCount": len(SCENARIOS),
        "rows": [],
        "status": {"overall": "FAIL"},
    }
    engine: subprocess.Popen[str] | None = None
    cache_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-natural-breadth-cache-", ignore_cleanup_errors=True)
    error: Exception | None = None
    try:
        if not model.is_dir():
            raise RuntimeError(f"model folder missing: {model}")
        report["memoryPreflight"] = live_batch.live_batch_memory_preflight(model, 1)
        port = free_port()
        base_url = f"http://127.0.0.1:{port}"
        report["baseUrl"] = base_url
        engine = launch_engine(model, port, Path(cache_tmp.name))
        report["health"] = wait_health(base_url, engine)
        report["cacheBefore"] = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)
        rows = [run_scenario(base_url, model, scenario) for scenario in SCENARIOS]
        report["cacheAfter"] = request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)
        row_status = "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL"
        prompt_status = "PASS" if all(row["promptExactToolCallBlocksPresent"] is False for row in rows) else "FAIL"
        status = {
            "memoryPreflight": "PASS",
            "naturalPrompts": prompt_status,
            "modelSelectedExpectedTools": row_status,
            **cache_status(report["cacheAfter"]),
        }
        status["overall"] = "PASS" if all(value == "PASS" for key, value in status.items() if key != "overall") else "FAIL"
        report.update(
            {
                "ok": status["overall"] == "PASS",
                "status": status,
                "rows": rows,
                "scenarioPassCount": sum(1 for row in rows if row["status"] == "PASS"),
                "selectedToolSequence": [row.get("selectedTool") for row in rows],
                "expectedToolSequence": [scenario.expected_tool for scenario in SCENARIOS],
                "finishedAt": timestamp(),
                "generatedAt": timestamp(),
                "notes": [
                    "This is direct-engine breadth evidence, not a Swift app-loop proof.",
                    "The model received natural objectives plus OpenAI tool schemas; prompts contain no serialized tool-call blocks.",
                    "No tools were executed by this proof; it validates autonomous first-tool selection only.",
                ],
            }
        )
        if not report["ok"]:
            raise AssertionError("natural breadth tool-choice checks failed")
    except Exception as exc:
        error = exc
        report.update({"ok": False, "error": f"{type(exc).__name__}: {exc}", "finishedAt": timestamp(), "generatedAt": timestamp()})
    finally:
        if engine is not None:
            terminate_process_group(engine)
            report["engineLogTail"] = read_output_tail(engine)
        cache_tmp.cleanup()
        write_report(output, report)
    if error is not None:
        raise error
    print(f"real-Qwen natural breadth tool-choice proof passed: {output}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"real-Qwen natural breadth tool-choice proof failed: {exc}", flush=True)
        raise SystemExit(1)
