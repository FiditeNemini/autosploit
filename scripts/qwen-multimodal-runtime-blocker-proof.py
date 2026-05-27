#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
MLLM_SOURCE = ROOT / "ExploitBotEngine" / "vmlx_engine" / "models" / "mllm.py"
ZAYA_SOURCE = ROOT / "ExploitBotEngine" / "vmlx_engine" / "models" / "zaya1_vl.py"
SIMPLE_ENGINE = ROOT / "ExploitBotEngine" / "vmlx_engine" / "engine" / "simple.py"
SERVER = ROOT / "ExploitBotEngine" / "vmlx_engine" / "server.py"
SYSTEM_REVIEW = ROOT / "docs" / "app-system-review-2026-05-21.md"


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


def assert_source_boundary() -> None:
    mllm = MLLM_SOURCE.read_text(encoding="utf-8")
    zaya = ZAYA_SOURCE.read_text(encoding="utf-8")
    simple = SIMPLE_ENGINE.read_text(encoding="utf-8")
    server = SERVER.read_text(encoding="utf-8")

    required_loader_tokens = [
        "class MLXMultimodalLM",
        "from mlx_vlm import generate",
        "from mlx_vlm import stream_generate",
        "register_mlx_vlm_zaya1_vl",
    ]
    missing_loader = [token for token in required_loader_tokens if token not in mllm]
    if missing_loader:
        raise AssertionError(f"mllm loader missing runtime tokens: {missing_loader}")
    if "raise NotImplementedError" in mllm:
        raise AssertionError("MLLM loader is still a NotImplementedError stub")
    if "class Model" not in zaya or "register_mlx_vlm_zaya1_vl" not in zaya:
        raise AssertionError("ZAYA1-VL runtime adapter missing")

    if "from ..models.mllm import MLXMultimodalLM" not in simple:
        raise AssertionError("SimpleEngine no longer imports the MLLM loader")
    if "self._model = MLXMultimodalLM(" not in simple:
        raise AssertionError("SimpleEngine no longer routes force/autodetected MLLM loads through MLXMultimodalLM")
    if "--mllm" not in server or "preserve_multimodal=engine.is_mllm" not in server:
        raise AssertionError("server multimodal request surface changed without proof update")


def run() -> None:
    assert_source_boundary()

    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        ledger = request("GET", "/qa/gap-ledger")
        qwen_gap = (ledger.get("gapContracts") or {}).get("qwenMultimodalRuntime") or {}
        proofs = qwen_gap.get("proofs") or []
        if "qwen-multimodal-runtime-blocker-proof.py" not in proofs:
            raise AssertionError(f"gap ledger missing qwen multimodal runtime proof: {qwen_gap}")
        if ledger.get("qwenMultimodalProofCount") != len(proofs):
            raise AssertionError(f"gap ledger qwen proof count mismatch: {ledger}")
        if ledger.get("qwenMultimodalProofFileParity") is not True:
            raise AssertionError(f"gap ledger qwen proof-file parity mismatch: {ledger}")
        if qwen_gap.get("status") != "in_progress":
            raise AssertionError(f"qwen multimodal gap should be marked in_progress for shipped runtime work: {qwen_gap}")
        if qwen_gap.get("blockedModelKinds") not in ([], None):
            raise AssertionError(f"qwen multimodal gap should not carry hard blocked model kinds yet: {qwen_gap}")
        if qwen_gap.get("promotionReady") is not False:
            raise AssertionError(f"qwen multimodal promotion readiness should remain false until live proofs exist: {qwen_gap}")

        docs = SYSTEM_REVIEW.read_text(encoding="utf-8")
        for token in ["qwen-multimodal-runtime-blocker-proof.py", "MLXMultimodalLM"]:
            if token not in docs:
                raise AssertionError(f"system review missing runtime blocker token {token}")

        print("qwen-multimodal-runtime-blocker proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"qwen-multimodal-runtime-blocker proof failed: {exc}", flush=True)
        raise SystemExit(1)
