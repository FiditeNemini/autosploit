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


def request(method: str, path: str, body: str | dict | None = None, timeout: float = 8.0):
    if isinstance(body, dict):
        body = json.dumps(body)
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


def write_fixture(path: Path) -> None:
    path.mkdir(parents=True)
    (path / "config.json").write_text(json.dumps({"model_type": "qwen3"}) + "\n", encoding="utf-8")
    (path / "jang_config.json").write_text(json.dumps({"format": "jang"}) + "\n", encoding="utf-8")
    (path / "jangtq_config.json").write_text(json.dumps({"format": "jangtq"}) + "\n", encoding="utf-8")
    (path / "generation_config.json").write_text(json.dumps({"temperature": 0.61, "top_p": 0.92}) + "\n", encoding="utf-8")
    (path / "tokenizer_config.json").write_text(json.dumps({"chat_template": "qwen qa"}) + "\n", encoding="utf-8")


def model_picker_state() -> dict:
    state = request("GET", "/state")
    picker = state.get("modelFolderPicker") or {}
    if "isVisible" not in picker:
        raise AssertionError(f"model folder picker state missing: {state.keys()}")
    return picker


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        initial = model_picker_state()
        if initial.get("isVisible") is not False:
            raise AssertionError(f"model picker should start hidden: {initial}")

        opened = request("POST", "/qa/model-folder-picker", {"action": "open"})
        if opened.get("ok") is not True:
            raise AssertionError(f"model picker open failed: {opened}")
        picker = model_picker_state()
        if picker.get("lastAction") != "open" or picker.get("isVisible") is not True:
            raise AssertionError(f"model picker open state mismatch: {picker}")

        cancelled = request("POST", "/qa/model-folder-picker", {"action": "cancel"})
        if cancelled.get("ok") is not True:
            raise AssertionError(f"model picker cancel failed: {cancelled}")
        picker = model_picker_state()
        if picker.get("lastAction") != "cancel" or picker.get("isVisible") is not False:
            raise AssertionError(f"model picker cancel state mismatch: {picker}")

        with tempfile.TemporaryDirectory(prefix="exploitbot-picker-model-") as tmp:
            model = Path(tmp) / "Qwen3-JANGTQ-Picker"
            write_fixture(model)
            selected = request("POST", "/qa/model-folder-picker", {"action": "select", "path": str(model)})
            if selected.get("ok") is not True:
                raise AssertionError(f"model picker select failed: {selected}")
            state = request("GET", "/state")
            picker = state.get("modelFolderPicker") or {}
            info = state.get("modelFolderInfo") or {}
            engine = state.get("engineConfig") or {}

            if picker.get("lastAction") != "select" or picker.get("isVisible") is not False:
                raise AssertionError(f"model picker select state mismatch: {picker}")
            if picker.get("selectedPath") != str(model) or picker.get("family") != "Qwen":
                raise AssertionError(f"model picker selection metadata mismatch: {picker}")
            if engine.get("modelPath") != str(model):
                raise AssertionError(f"engine model path was not updated from picker: {engine}")
            for key in ("hasConfig", "hasJangConfig", "hasJangtqConfig", "hasGenerationConfig", "hasTokenizerConfig"):
                if info.get(key) is not True:
                    raise AssertionError(f"selected model did not expose {key}: {info}")
            if "Qwen" not in info.get("family", "") or info.get("isSupported") is not True:
                raise AssertionError(f"selected model support state wrong: {info}")

        print("model-folder-picker proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"model-folder-picker proof failed: {exc}", flush=True)
        raise SystemExit(1)
