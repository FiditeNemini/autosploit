#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
RELEASE_QWEN_PROOF = ROOT / "scripts" / "release-app-live-qwen-proof.py"
RELEASE_APP_LITERAL = "release/ExploitBot.app"
MODEL_27B = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP")
MODEL_35B = Path("/Users/eric/models/dealign.ai/Qwen3.6-35B-A3B-MXFP8-CRACK-MTP")
OUTPUT_27B = ROOT / "docs/live-proofs/2026-07-05-release-app-live-qwen-27b-tool-loop-current.json"
OUTPUT_35B = ROOT / "docs/live-proofs/2026-07-05-release-app-live-qwen-35b-tool-loop-current.json"
TARGET_CVE = os.environ.get("EXPLOITBOT_RELEASE_QWEN_TOOL_CVE", "CVE-2025-49704")
FINAL_MARKER = "RELEASE_QWEN_TOOL_LOOP_FINAL"


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
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:8000]
        raise AssertionError(message + suffix)


def output_for_model(model: Path) -> Path:
    explicit = os.environ.get("EXPLOITBOT_RELEASE_QWEN_TOOL_OUTPUT")
    if explicit:
        return Path(explicit).expanduser()
    if "35b" in str(model).lower():
        return OUTPUT_35B
    return OUTPUT_27B


def proof_prompt() -> str:
    return (
        f"Authorized packaged release Qwen tool-loop proof. Reasoning is off. Use the lookup_cve tool exactly once for {TARGET_CVE}. "
        "Do not use search_cve, search_context, run_shell, or external commands. "
        f"If you need to call the tool, emit the Qwen tool call for lookup_cve with cve_id set to {TARGET_CVE}. "
        f"After the lookup_cve tool result, answer with exact marker {FINAL_MARKER}, the CVE ID, and one sentence summarizing impact."
    )


def wait_for_lookup_completion(timeout: float = 300.0) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    deadline = time.time() + timeout
    last: tuple[list[dict[str, Any]], dict[str, Any]] | None = None
    while time.time() < deadline:
        messages = release.app_request("GET", "/messages", timeout=5.0)
        state = release.app_request("GET", "/state", timeout=5.0)
        last = (messages, state)
        has_tool = any(m.get("tool") == "lookup_cve" for m in messages)
        has_final = any(m.get("role") == "assistant" and FINAL_MARKER in str(m.get("content") or "") for m in messages)
        if has_tool and has_final and not state.get("isWorking") and not state.get("isStreaming"):
            return messages, state
        time.sleep(0.5)
    raise AssertionError("timed out waiting for release-app lookup_cve final answer", {"last": last})


def runtime_status(health: dict[str, Any], report: dict[str, Any]) -> dict[str, str]:
    effective = health.get("effective_config") or {}
    cache = effective.get("cache") or {}
    topology = cache.get("topology") or {}
    kv = cache.get("kv_cache_quantization") or {}
    mtp = health.get("mtp") or {}
    tool_loop = report.get("toolLoop") or {}
    return {
        "appBundledRuntime": "PASS" if report.get("appBundledRuntime") else "FAIL",
        "realModelLoaded": "PASS" if report.get("realModelLoaded") else "FAIL",
        "lookupCVEOnlyTool": "PASS" if tool_loop.get("toolSequence") == ["lookup_cve"] else "FAIL",
        "lookupCVEVerboseTranscript": "PASS" if tool_loop.get("verboseTranscript") is True else "FAIL",
        "finalAnswerMarker": "PASS" if FINAL_MARKER in str(tool_loop.get("finalAnswer") or "") else "FAIL",
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


def extract_tool_loop(messages: list[dict[str, Any]]) -> dict[str, Any]:
    tool_messages = [m for m in messages if m.get("tool") == "lookup_cve"]
    sequence = [m.get("tool") for m in messages if m.get("tool")]
    final_answers = [
        str(m.get("content") or "")
        for m in messages
        if m.get("role") == "assistant" and FINAL_MARKER in str(m.get("content") or "")
    ]
    first_tool = tool_messages[0] if tool_messages else {}
    tool_content = str(first_tool.get("content") or "")
    return {
        "targetCVE": TARGET_CVE,
        "toolSequence": sequence,
        "toolMessageCount": len(tool_messages),
        "toolTranscriptPreview": tool_content[:4000],
        "verboseTranscript": (
            "Tool request: lookup_cve" in tool_content
            and TARGET_CVE in tool_content
            and "Missing cve_id parameter" not in tool_content
            and ("Sources:" in tool_content or "Description:" in tool_content)
        ),
        "finalAnswer": final_answers[-1] if final_answers else "",
    }


def apply_release_settings(model: Path) -> dict[str, Any]:
    return release.app_request(
        "POST",
        "/qa/apply-app-settings",
        {
            "maxIterations": 4,
            "toolSchemaMaxTools": 32,
            "includeUnavailableToolSchemas": True,
            "forceFinalAnswerAfterToolResults": True,
            "engine": {
                "modelPath": str(model),
                "useModelGenerationDefaults": False,
                "maxTokens": 256,
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


def main() -> None:
    model = Path(os.environ.get("EXPLOITBOT_RELEASE_QWEN_MODEL", str(MODEL_27B))).expanduser()
    output = output_for_model(model)
    require(RELEASE_APP_LITERAL in str(release.APP), "release helper app path does not point at release/ExploitBot.app", str(release.APP))
    require(release.APP_BINARY.is_file(), "release app binary is missing; run script/package_release.sh first")
    require(model.is_dir(), f"Qwen model folder is missing: {model}")

    release.terminate_release_engine_processes()
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    home_tmp = tempfile.TemporaryDirectory(prefix="exploitbot-release-qwen-tool-home-")
    env = {**os.environ, "EXPLOITBOT_TESTING": "1", "PYTHONDONTWRITEBYTECODE": "1", "HOME": home_tmp.name}
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "release-app-live-qwen-tool-loop",
        "app": str(release.APP),
        "model": str(model),
        "targetCVE": TARGET_CVE,
        "startedAt": timestamp(),
    }
    error: Exception | None = None
    app: subprocess.Popen[bytes] | None = None

    try:
        report["memoryPreflight"] = release.wait_for_release_qwen_memory_slot(model)
        app = subprocess.Popen([str(release.APP_BINARY)], cwd=ROOT, env=env)
        release.wait_for_app()
        runtime = release.app_request("GET", "/qa/engine-python-runtime")
        selected = runtime.get("selected") or {}
        require(selected.get("source") == "app-bundled-vmlx-python", "release app did not select app-bundled vMLX Python", runtime)
        require(selected.get("missingModuleCount") == 0, "release app bundled Python is missing engine modules", runtime)
        report["runtime"] = runtime
        report["appBundledRuntime"] = True

        selected_model = release.app_request("POST", "/qa/model-folder", str(model))
        require(selected_model.get("ok") is True, "model folder selection failed", selected_model)
        settings = apply_release_settings(model)
        require(settings.get("ok") is True, "release app settings apply failed before engine start", settings)
        report["settings"] = settings

        started = release.app_request("POST", "/engine/start")
        require(started.get("ok") is True, "engine start request failed", started)
        state = release.wait_for_engine()
        port = int(state["enginePort"])
        base_url = f"http://127.0.0.1:{port}"
        health = release.request_json("GET", f"{base_url}/health", timeout=10.0)
        report["realModelLoaded"] = bool(health.get("model_name") or model.name)

        release.app_request("POST", "/mode", "autopilot", timeout=15.0)
        release.app_request("POST", "/reasoning", "off", timeout=15.0)
        catalog = release.app_request(
            "POST",
            "/qa/tool-catalog",
            {"query": proof_prompt(), "tab": "supplyChain", "maxTools": 32, "includeUnavailable": True},
            timeout=15.0,
        )
        require("lookup_cve" in (catalog.get("toolNames") or []), "lookup_cve schema missing before release-app Qwen turn", catalog)
        report["toolCatalog"] = catalog

        release.app_request("POST", "/send", proof_prompt(), timeout=15.0)
        messages, final_state = wait_for_lookup_completion()
        cache_after = release.request_json("GET", f"{base_url}/v1/cache/stats", timeout=15.0)
        tool_loop = extract_tool_loop(messages)
        require(tool_loop["toolSequence"] == ["lookup_cve"], "unexpected release-app Qwen tool sequence", tool_loop)
        require(tool_loop["verboseTranscript"] is True, "release-app lookup_cve verbose transcript missing detail", tool_loop)
        require(FINAL_MARKER in tool_loop["finalAnswer"] and TARGET_CVE in tool_loop["finalAnswer"], "release-app final marker/CVE missing", tool_loop)

        report.update(
            {
                "state": final_state,
                "engineState": state,
                "health": health,
                "cacheAfter": cache_after,
                "messages": messages,
                "toolLoop": tool_loop,
            }
        )
    except Exception as exc:
        error = exc
        report["error"] = f"{type(exc).__name__}: {exc}"
        try:
            report["messages"] = release.app_request("GET", "/messages", timeout=5.0)
            report["state"] = release.app_request("GET", "/state", timeout=5.0)
        except Exception:
            pass
    finally:
        try:
            release.app_request("POST", "/engine/stop", timeout=20.0)
        except Exception:
            pass
        production_stop_rows = release.release_engine_process_rows()
        report["productionStopProcessRows"] = production_stop_rows
        report["productionStopClean"] = not production_stop_rows
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
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
        report["status"] = runtime_status(report.get("health") or {}, report)
        report["ok"] = all(value == "PASS" for value in report["status"].values())
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error is not None:
        raise error
    require(report["ok"] is True, "release app live Qwen tool-loop proof failed", report)
    signed = subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(release.APP)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    require(signed.returncode == 0, "release app signature failed after live Qwen tool-loop run", signed.stdout)
    print(f"release-app-live-qwen-tool-loop proof passed and wrote {output}")


if __name__ == "__main__":
    try:
        with app_proof_lock("release-app-live-qwen-tool-loop-proof.py"):
            main()
    except Exception as exc:
        print(f"release-app-live-qwen-tool-loop proof failed: {exc}", flush=True)
        raise SystemExit(1)
