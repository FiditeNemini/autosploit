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


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"


def request(method: str, path: str, body: str | None = None, timeout: float = 8.0):
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


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


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        with tempfile.TemporaryDirectory(prefix="exploitbot-unsupported-model-") as tmp:
            root = Path(tmp)
            fixtures = [
                ("Gemma-Unsupported", "gemma3"),
                ("ZAYA1-VL-JANG", "zaya1_vl"),
            ]
            for folder_name, model_type in fixtures:
                model = root / folder_name
                model.mkdir()
                (model / "config.json").write_text(json.dumps({"model_type": model_type}) + "\n", encoding="utf-8")
                (model / "generation_config.json").write_text(json.dumps({"temperature": 0.7}) + "\n", encoding="utf-8")
                response = request("POST", "/qa/model-folder", str(model))
                if response.get("ok") is not True:
                    raise AssertionError(f"model folder route failed: {response}")

                started = request("POST", "/engine/start")
                if started.get("ok") is not True:
                    raise AssertionError(f"engine start route failed: {started}")
                time.sleep(0.7)
                state = request("GET", "/state")

                info = state.get("modelFolderInfo") or {}
                if info.get("isSupported") is not False:
                    raise AssertionError(f"unsupported fixture was not marked unsupported: {info}")
                if state.get("engineRunning") is True:
                    raise AssertionError(f"engine started for unsupported model folder: {state}")
                error = state.get("engineError") or ""
                if "Only Qwen and MiniMax" not in error or "blocked" not in error.lower():
                    raise AssertionError(f"unsupported start did not expose blocking error: {state}")

        print("unsupported-model-start proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"unsupported-model-start proof failed: {exc}", flush=True)
        raise SystemExit(1)
