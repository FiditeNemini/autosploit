#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_MANAGER = ROOT / "ExploitBot" / "Sources" / "ExploitBot" / "Services" / "EngineManager.swift"
APP_API = "http://127.0.0.1:9999"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def request(method: str, path: str, timeout: float = 8.0):
    req = urllib.request.Request(f"{APP_API}{path}", method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_for_app(timeout: float = 15.0) -> None:
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


def assert_runtime_route() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)
    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        payload = request("GET", "/qa/engine-python-runtime")
        require(payload.get("ok") is True, f"engine Python runtime route failed: {payload}")
        selected = payload.get("selected") or {}
        require(selected.get("valid") is True, f"selected engine Python runtime is not valid: {payload}")
        require(selected.get("missingModuleCount") == 0, f"selected runtime has missing modules: {payload}")
        require(payload.get("candidateCount", 0) >= 3, f"runtime candidate inventory is too narrow: {payload}")
        for module in ("fastapi", "uvicorn", "mlx", "mlx_lm", "transformers", "numpy", "vmlx_engine"):
            require(module in (payload.get("requiredModules") or []), f"runtime route missing required module {module}: {payload}")
        state = request("GET", "/state")
        require("/qa/engine-python-runtime" in ((state.get("qaCoverage") or {}).get("stateRoutes") or []), "state route list missing engine Python runtime route")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


def main() -> None:
    source = ENGINE_MANAGER.read_text(encoding="utf-8")

    require("struct EnginePythonRuntime" in source, "EnginePythonRuntime diagnostic model is missing")
    require("EXPLOITBOT_ENGINE_PYTHON" in source, "engine Python env override is missing")
    require("bundled-python/python/bin/python3" in source, "bundled vMLX Python candidate is missing")
    require("/Applications/vMLX.app/Contents/Resources/bundled-python/python/bin/python3" in source, "installed vMLX Python candidate is missing")
    require("ExploitBotEngine/.venv/bin/python3" in source, "repo-local engine venv candidate is missing")
    require("requiredPythonModules" in source, "required Python module list is missing")
    for module in ("fastapi", "uvicorn", "mlx", "mlx_lm", "transformers", "numpy"):
        require(f'"{module}"' in source, f"required Python module {module} is not checked")
    require("validatePythonRuntime" in source, "Python runtime validation function is missing")
    require("PYTHONDONTWRITEBYTECODE" in source, "Python runtime checks must not mutate signed app resources with __pycache__ files")
    require("pythonRuntimeSnapshot" in source, "Python runtime QA snapshot is missing")
    require("missingModules" in source, "missing module diagnostics are not surfaced")
    require("Python runtime is missing required modules" in source, "user-facing missing dependency error is missing")
    require("lastPythonRuntime" in source, "selected Python runtime is not retained for UI/QA diagnostics")
    require("lastPythonRuntimeDiagnostics" in source, "Python runtime candidate diagnostics are not retained")

    start_body = re.search(r"func start\(config: EngineConfig\) async \{(?P<body>.*?)var args =", source, re.S)
    require(start_body is not None, "could not locate EngineManager.start pre-launch section")
    require("resolvePythonRuntime" in start_body.group("body"), "start() does not resolve a validated Python runtime before launch")
    require("runtime.path" in source, "Process executable is not wired to the selected runtime path")

    app_state = (ROOT / "ExploitBot" / "Sources" / "ExploitBot" / "Models" / "AppState.swift").read_text(encoding="utf-8")
    require('"/qa/engine-python-runtime"' in app_state, "engine Python runtime QA route is missing")
    require("state.engineManager.pythonRuntimeSnapshot()" in app_state, "QA route does not call EngineManager runtime snapshot")
    assert_runtime_route()

    print("engine-python-runtime-resolution proof passed")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"engine-python-runtime-resolution proof failed: {exc}", flush=True)
        raise SystemExit(1)
