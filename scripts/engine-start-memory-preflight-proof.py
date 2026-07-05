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
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
DEFAULT_MODEL = Path("/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP")
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-engine-start-memory-preflight-block.json"


def request_json(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 10.0) -> dict[str, Any]:
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_until(predicate, label: str, timeout: float = 30.0):
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
    raise AssertionError(f"timed out waiting for {label}; last={last}")


def launch_py_processes() -> list[str]:
    output = subprocess.check_output(["/bin/ps", "-axo", "command="], text=True)
    return [
        line
        for line in output.splitlines()
        if "ExploitBotEngine/launch.py" in line and "engine-start-memory-preflight-proof.py" not in line
    ]


def blocked_preflight_state() -> dict[str, Any] | None:
    state = request_json("GET", "/state", timeout=2.0)
    preflight = state.get("engineMemoryPreflight")
    if isinstance(preflight, dict) and preflight.get("allowed") is False:
        return state
    if "Engine start blocked by RAM preflight" in str(state.get("engineError") or ""):
        return state
    return None


def main() -> None:
    model = Path(os.environ.get("EXPLOITBOT_ENGINE_PREFLIGHT_MODEL", str(DEFAULT_MODEL))).expanduser()
    output = Path(os.environ.get("EXPLOITBOT_ENGINE_PREFLIGHT_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    if not model.is_dir():
        raise AssertionError(f"model folder missing for preflight proof: {model}")

    report: dict[str, Any] = {
        "ok": False,
        "proofType": "engine-start-memory-preflight-block-no-model-load",
        "model": str(model),
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    app: subprocess.Popen[str] | None = None
    app_home = tempfile.TemporaryDirectory(prefix="exploitbot-engine-preflight-home-")
    error: Exception | None = None
    try:
        subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT, check=True)
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        before = launch_py_processes()
        report["launchPyBefore"] = before

        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["EXPLOITBOT_ENGINE_MIN_AVAILABLE_GB"] = "9999"
        env["EXPLOITBOT_DATA_DIR"] = str(Path(app_home.name) / ".exploitbot" / "data")
        app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
        wait_until(lambda: request_json("GET", "/state", timeout=1.0), "app test server")

        request_json(
            "POST",
            "/qa/apply-app-settings",
            {
                "engine": {
                    "modelPath": str(model),
                    "useModelGenerationDefaults": True,
                    "kvCacheQuantization": "turboquant-q4",
                    "prefixCache": True,
                    "pagedCache": True,
                    "blockDiskCache": True,
                }
            },
        )
        request_json("POST", "/engine/start", timeout=5.0)
        state = wait_until(blocked_preflight_state, "RAM preflight block")
        after = launch_py_processes()
        preflight = state.get("engineMemoryPreflight") or {}

        report.update(
            {
                "ok": True,
                "state": state,
                "engineMemoryPreflight": preflight,
                "launchPyAfter": after,
                "noLaunchPyStarted": before == after,
                "forcedRequiredAvailableGB": 9999,
            }
        )
        if preflight.get("allowed") is not False:
            raise AssertionError(f"engine memory preflight did not block: {preflight}")
        if float(preflight.get("requiredAvailableGB") or 0) != 9999.0:
            raise AssertionError(f"forced memory floor was not applied: {preflight}")
        if before != after:
            raise AssertionError(f"launch.py process appeared despite RAM preflight block: before={before} after={after}")
    except Exception as exc:
        error = exc
        report.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app_home.cleanup()
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error is not None:
        raise error
    print("engine-start-memory-preflight proof passed")


if __name__ == "__main__":
    main()
