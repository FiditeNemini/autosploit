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


def write_fixture(path: Path, model_type: str, with_jang: bool = True) -> None:
    path.mkdir(parents=True)
    (path / "config.json").write_text(json.dumps({"model_type": model_type}) + "\n", encoding="utf-8")
    (path / "generation_config.json").write_text(json.dumps({"temperature": 0.7}) + "\n", encoding="utf-8")
    (path / "tokenizer_config.json").write_text(json.dumps({"chat_template": "qa"}) + "\n", encoding="utf-8")
    if with_jang:
        (path / "jang_config.json").write_text(json.dumps({"format": "jangtq"}) + "\n", encoding="utf-8")


def inspect_fixture(path: Path) -> dict:
    response = request("POST", "/qa/model-folder", str(path))
    if response.get("ok") is not True:
        raise AssertionError(f"model folder route failed: {response}")
    return request("GET", "/state").get("modelFolderInfo") or {}


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        with tempfile.TemporaryDirectory(prefix="exploitbot-model-fixtures-") as tmp:
            root = Path(tmp)
            qwen = root / "Qwen3.5-JANG"
            qwen_vl = root / "Qwen3-VL-JANG"
            minimax = root / "MiniMax-M2-JANGTQ"
            unsupported = root / "Gemma-Unsupported"
            write_fixture(qwen, "qwen3")
            write_fixture(qwen_vl, "qwen3_vl")
            write_fixture(minimax, "minimax_text")
            write_fixture(unsupported, "gemma3")

            qwen_info = inspect_fixture(qwen)
            if qwen_info.get("family") != "Qwen" or qwen_info.get("isSupported") is not True:
                raise AssertionError(f"qwen fixture not supported: {qwen_info}")
            if qwen_info.get("hasGenerationConfig") is not True or qwen_info.get("hasJangConfig") is not True:
                raise AssertionError(f"qwen fixture did not expose config files: {qwen_info}")
            if "auto-detect" not in qwen_info.get("supportMessage", ""):
                raise AssertionError(f"qwen support message did not mention autodetect: {qwen_info}")

            qwen_vl_info = inspect_fixture(qwen_vl)
            if qwen_vl_info.get("family") != "Qwen" or qwen_vl_info.get("isSupported") is not False:
                raise AssertionError(f"qwen vl fixture should be blocked until multimodal support is enabled: {qwen_vl_info}")
            if qwen_vl_info.get("isMultimodal") is not True:
                raise AssertionError(f"qwen vl fixture did not expose multimodal flag: {qwen_vl_info}")
            qwen_vl_warning = qwen_vl_info.get("supportMessage", "")
            if "multimodal" not in qwen_vl_warning.lower() or "not yet supported" not in qwen_vl_warning.lower():
                raise AssertionError(f"qwen vl warning missing multimodal unsupported language: {qwen_vl_info}")

            minimax_info = inspect_fixture(minimax)
            if minimax_info.get("family") != "MiniMax" or minimax_info.get("isSupported") is not True:
                raise AssertionError(f"minimax fixture not supported: {minimax_info}")
            if "full-KV" not in minimax_info.get("supportMessage", ""):
                raise AssertionError(f"minimax support message did not mention full-KV cache topology: {minimax_info}")

            unsupported_info = inspect_fixture(unsupported)
            if unsupported_info.get("isSupported") is not False:
                raise AssertionError(f"unsupported fixture incorrectly supported: {unsupported_info}")
            warning = unsupported_info.get("supportMessage", "")
            if "Only Qwen and MiniMax" not in warning or "parser/cache" not in warning:
                raise AssertionError(f"unsupported warning missing required language: {unsupported_info}")

        print("model-folder-warning proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"model-folder-warning proof failed: {exc}", flush=True)
        raise SystemExit(1)
