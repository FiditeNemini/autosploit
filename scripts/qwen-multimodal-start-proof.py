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

        with tempfile.TemporaryDirectory(prefix="exploitbot-qwen-model-") as tmp:
            text_model = Path(tmp) / "Qwen3.6-Text-JANG"
            text_model.mkdir()
            (text_model / "config.json").write_text(
                json.dumps(
                    {
                        "model_type": "qwen3_5",
                        "architectures": ["Qwen3_5ForConditionalGeneration"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (text_model / "generation_config.json").write_text(json.dumps({"temperature": 0.7}) + "\n", encoding="utf-8")
            (text_model / "jang_config.json").write_text(json.dumps({"format": "jang"}) + "\n", encoding="utf-8")
            response = request("POST", "/qa/model-folder", str(text_model))
            if response.get("ok") is not True:
                raise AssertionError(f"qwen text-capable model folder route failed: {response}")
            state = request("GET", "/state")
            info = state.get("modelFolderInfo") or {}
            if info.get("family") != "Qwen":
                raise AssertionError(f"qwen text-capable fixture did not retain Qwen family: {info}")
            if info.get("isMultimodal") is not False:
                raise AssertionError(f"qwen text-capable fixture should not be blocked as multimodal: {info}")
            if info.get("isSupported") is not True:
                raise AssertionError(f"qwen text-capable fixture should be startable in text mode: {info}")

            model = Path(tmp) / "Qwen3-VL-JANGTQ"
            model.mkdir()
            (model / "config.json").write_text(
                json.dumps(
                    {
                        "model_type": "qwen3_vl",
                        "vision_config": {"hidden_size": 1024},
                        "image_token_index": 151655,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (model / "generation_config.json").write_text(json.dumps({"temperature": 0.7}) + "\n", encoding="utf-8")
            (model / "jang_config.json").write_text(json.dumps({"format": "jangtq"}) + "\n", encoding="utf-8")

            response = request("POST", "/qa/model-folder", str(model))
            if response.get("ok") is not True:
                raise AssertionError(f"model folder route failed: {response}")
            info = request("GET", "/state").get("modelFolderInfo") or {}
            if info.get("family") != "Qwen":
                raise AssertionError(f"qwen multimodal fixture did not retain Qwen family: {info}")
            if info.get("isMultimodal") is not True:
                raise AssertionError(f"qwen multimodal fixture missing multimodal flag: {info}")
            if info.get("isSupported") is not True:
                raise AssertionError(f"qwen multimodal fixture should be supported now: {info}")

            # Optional live start smoke against a real local multimodal Qwen model to verify
            # we can reach the start endpoint without the legacy modal block.
            live_qwen = os.environ.get("EXPLOITBOT_QWEN_SMOKE_MODEL", "").strip()
            if live_qwen:
                live_model = Path(live_qwen).expanduser()
                if live_model.is_dir():
                    response = request("POST", "/qa/model-folder", str(live_model))
                    if response.get("ok") is not True:
                        raise AssertionError(f"live qwen model folder route failed: {response}")
                    started = request("POST", "/engine/start")
                    if started.get("ok") is not True:
                        raise AssertionError(f"live qwen engine start request failed: {started}")
                    time.sleep(0.8)
                    live_state = request("GET", "/state")
                    if live_state.get("healthStatus") == "blocked":
                        raise AssertionError(f"live qwen start still blocked in-app: {live_state}")
                    request("POST", "/engine/stop")

        print("qwen-multimodal-start proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"qwen-multimodal-start proof failed: {exc}", flush=True)
        raise SystemExit(1)
