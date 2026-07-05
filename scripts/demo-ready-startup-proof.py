#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
MODEL_27B = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP")
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-demo-ready-startup.json"


def request(method: str, path: str, body: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_for_app(timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            request("GET", "/state", timeout=1.0)
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"app test server did not become ready: {last_error}")


def launch_app(env: dict[str, str]) -> subprocess.Popen[str]:
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    proc = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)
    if proc.wait(timeout=45) != 0:
        raise RuntimeError("build_and_run --verify failed")
    wait_for_app()
    return proc


def stop_app(proc: subprocess.Popen[str] | None = None) -> None:
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if proc is not None and proc.poll() is None:
        proc.send_signal(signal.SIGTERM)


def engine_config(state: dict[str, Any]) -> dict[str, Any]:
    return state.get("engineConfig") if isinstance(state.get("engineConfig"), dict) else {}


def show_onboarding(state: dict[str, Any]) -> bool | None:
    mode = state.get("modeSelection") if isinstance(state.get("modeSelection"), dict) else {}
    value = mode.get("showOnboarding")
    return value if isinstance(value, bool) else None


def active_op_name(state: dict[str, Any]) -> str:
    mode = state.get("modeSelection") if isinstance(state.get("modeSelection"), dict) else {}
    return str(mode.get("activeOpName") or "")


def status_from_states(
    *,
    first_state: dict[str, Any],
    relaunched_state: dict[str, Any],
    expected_model: str,
) -> dict[str, str]:
    first_engine = engine_config(first_state)
    relaunched_engine = engine_config(relaunched_state)
    return {
        "firstLaunchOnboardingDismissed": "PASS" if show_onboarding(first_state) is False else "FAIL",
        "relaunchOnboardingDismissed": "PASS" if show_onboarding(relaunched_state) is False else "FAIL",
        "modelPathPersisted": "PASS" if relaunched_engine.get("modelPath") == expected_model else "FAIL",
        "demoOpPersisted": "PASS" if active_op_name(relaunched_state) == "Demo Ready Qwen 27B" else "FAIL",
        "q4KV": "PASS" if relaunched_engine.get("kvCacheQuantization") == "turboquant-q4" else "FAIL",
        "prefixCache": "PASS" if relaunched_engine.get("prefixCache") is True else "FAIL",
        "pagedCache": "PASS" if relaunched_engine.get("pagedCache") is True else "FAIL",
        "promptL2Disk": "PASS" if relaunched_engine.get("promptL2Disk") is True else "FAIL",
        "blockL2Disk": "PASS" if relaunched_engine.get("blockL2Disk") is True else "FAIL",
        "noModelLoaded": "PASS" if first_state.get("engineRunning") is False and relaunched_state.get("engineRunning") is False else "FAIL",
    }


def main() -> None:
    output = Path(os.environ.get("EXPLOITBOT_DEMO_READY_STARTUP_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "demo-ready-startup",
        "proofLevel": "live-debug-app-isolated-data-dir-onboard-relaunch-no-model-load",
        "modelPath": str(MODEL_27B),
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-demo-ready-home-")
    app: subprocess.Popen[str] | None = None
    try:
        if not MODEL_27B.is_dir():
            raise AssertionError(f"27B model folder missing: {MODEL_27B}")
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = temp_home.name
        env["EXPLOITBOT_DATA_DIR"] = str(Path(temp_home.name) / ".exploitbot" / "data")

        app = launch_app(env)
        before = request("GET", "/state")
        onboarded = request("POST", "/qa/onboarding-complete", {
            "language": "en",
            "modelPath": str(MODEL_27B),
            "opName": "Demo Ready Qwen 27B",
            "mode": "autopilot",
            "scope": "127.0.0.1/32",
            "startEngine": False,
        })
        if onboarded.get("ok") is not True:
            raise AssertionError(f"onboarding completion failed: {onboarded}")
        first_state = request("GET", "/state")
        stop_app(app)
        app = None

        app = launch_app(env)
        relaunched_state = request("GET", "/state")
        status = status_from_states(
            first_state=first_state,
            relaunched_state=relaunched_state,
            expected_model=str(MODEL_27B),
        )
        report.update({
            "before": {
                "showOnboarding": show_onboarding(before),
                "engineRunning": before.get("engineRunning"),
            },
            "firstLaunch": {
                "showOnboarding": show_onboarding(first_state),
                "engineConfig": engine_config(first_state),
                "engineRunning": first_state.get("engineRunning"),
                "activeOpName": active_op_name(first_state),
            },
            "relaunch": {
                "showOnboarding": show_onboarding(relaunched_state),
                "engineConfig": engine_config(relaunched_state),
                "engineRunning": relaunched_state.get("engineRunning"),
                "activeOpName": active_op_name(relaunched_state),
            },
            "status": status,
            "ok": all(value == "PASS" for value in status.values()),
        })
        if report["ok"] is not True:
            raise AssertionError(f"demo-ready startup status failed: {status}")
    finally:
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        stop_app(app)
        temp_home.cleanup()

    print(f"demo-ready startup proof wrote {output}")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"demo-ready startup proof failed: {exc}", flush=True)
        raise SystemExit(1)
