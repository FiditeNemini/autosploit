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
    (path / "config.json").write_text(json.dumps({"model_type": "minimax_text"}) + "\n", encoding="utf-8")
    (path / "jang_config.json").write_text(json.dumps({"format": "jang"}) + "\n", encoding="utf-8")
    (path / "jangtq_config.json").write_text(json.dumps({"format": "jangtq"}) + "\n", encoding="utf-8")
    (path / "generation_config.json").write_text(json.dumps({"temperature": 0.72}) + "\n", encoding="utf-8")
    (path / "tokenizer_config.json").write_text(json.dumps({"chat_template": "minimax qa"}) + "\n", encoding="utf-8")


def picker_state() -> dict:
    state = request("GET", "/state")
    picker = state.get("modelFolderPicker") or {}
    if picker.get("source") != "onboarding":
        raise AssertionError(f"model picker did not record onboarding source: {picker}")
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

        opened = request("POST", "/qa/onboarding-model-picker", {"action": "open"})
        if opened.get("ok") is not True:
            raise AssertionError(f"onboarding model picker open failed: {opened}")
        picker = picker_state()
        if picker.get("lastAction") != "open" or picker.get("isVisible") is not True:
            raise AssertionError(f"onboarding model picker open state mismatch: {picker}")

        cancelled = request("POST", "/qa/onboarding-model-picker", {"action": "cancel"})
        if cancelled.get("ok") is not True:
            raise AssertionError(f"onboarding model picker cancel failed: {cancelled}")
        picker = picker_state()
        if picker.get("lastAction") != "cancel" or picker.get("isVisible") is not False:
            raise AssertionError(f"onboarding model picker cancel state mismatch: {picker}")

        with tempfile.TemporaryDirectory(prefix="exploitbot-onboarding-model-") as tmp:
            model = Path(tmp) / "MiniMax-M2-JANGTQ-Onboarding"
            write_fixture(model)

            selected = request("POST", "/qa/onboarding-model-picker", {"action": "select", "path": str(model)})
            if selected.get("ok") is not True:
                raise AssertionError(f"onboarding model picker select failed: {selected}")
            state = request("GET", "/state")
            picker = state.get("modelFolderPicker") or {}
            info = state.get("modelFolderInfo") or {}
            if picker.get("source") != "onboarding" or picker.get("family") != "MiniMax":
                raise AssertionError(f"onboarding picker selection source/family mismatch: {picker}")
            if info.get("hasJangtqConfig") is not True or info.get("hasGenerationConfig") is not True:
                raise AssertionError(f"onboarding selected folder missing config proof: {info}")

            completed = request("POST", "/qa/onboarding-complete", {
                "language": "en",
                "modelPath": str(model),
                "opName": "QA Onboarding Model Picker",
                "mode": "copilot",
                "scope": "192.0.2.0/24",
                "startEngine": False,
            })
            if completed.get("ok") is not True:
                raise AssertionError(f"onboarding completion failed: {completed}")
            state = request("GET", "/state")
            picker = state.get("modelFolderPicker") or {}
            mode = state.get("modeSelection") or {}
            if picker.get("source") != "onboarding" or picker.get("selectedPath") != str(model):
                raise AssertionError(f"onboarding completion did not preserve model picker state: {picker}")
            if mode.get("showOnboarding") is not False or mode.get("lastAction") != "complete-onboarding":
                raise AssertionError(f"onboarding completion mode state mismatch: {mode}")

        print("onboarding-model-picker proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"onboarding-model-picker proof failed: {exc}", flush=True)
        raise SystemExit(1)
