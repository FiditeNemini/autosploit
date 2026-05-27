#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = Path(os.environ.get("EXPLOITBOT_ZAYA_VL_MODEL", "/Users/eric/models/Osaurus/ZAYA1-VL-8B-MXFP4"))
IMAGE = MODEL / "osaurus-x-banner.png"
OUTPUT = ROOT / "docs/live-proofs/checkpoint-464-zaya-visual-live.json"
PYTHON = ROOT / "release/ExploitBot.app/Contents/Resources/bundled-python/python/bin/python3"
ENGINE = ROOT / "release/ExploitBot.app/Contents/Resources/ExploitBotEngine"


def run() -> None:
    if not PYTHON.is_file():
        raise AssertionError(f"bundled python missing: {PYTHON}")
    if not MODEL.is_dir():
        raise AssertionError(f"ZAYA VL model missing: {MODEL}")
    if not IMAGE.is_file():
        raise AssertionError(f"proof image missing: {IMAGE}")

    code = f"""
import json
from pathlib import Path
from vmlx_engine.api.utils import is_mllm_model
from vmlx_engine.models.mllm import MLXMultimodalLM

model_path = {str(MODEL)!r}
image_path = {str(IMAGE)!r}
if not is_mllm_model(model_path):
    raise AssertionError("ZAYA1-VL model did not route to MLLM")
m = MLXMultimodalLM(model_path)
messages = [{{
    "role": "user",
    "content": [
        {{"type": "image_url", "image_url": {{"url": image_path}}}},
        {{"type": "text", "text": "What is shown? Answer in 5 words."}},
    ],
}}]
out = m.chat(messages, max_tokens=8, temperature=0.0)
text = (out.text or "").strip()
payload = {{
    "ok": bool(text),
    "model": model_path,
    "image": image_path,
    "text": text,
    "promptTokens": out.prompt_tokens,
    "completionTokens": out.completion_tokens,
}}
print(json.dumps(payload))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ENGINE if ENGINE.is_dir() else ROOT / "ExploitBotEngine")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [str(PYTHON), "-c", code],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout)
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    payload = json.loads(lines[-1])
    text = payload.get("text", "").lower()
    if not payload.get("ok") or not any(token in text for token in ("dinosaur", "logo", "osaurus")):
        raise AssertionError(f"ZAYA visual answer did not describe the image: {payload}")
    if payload.get("promptTokens", 0) <= 0 or payload.get("completionTokens", 0) <= 0:
        raise AssertionError(f"ZAYA visual token accounting missing: {payload}")

    payload["proof"] = "zaya-visual-live-proof.py"
    payload["timestamp"] = datetime.now().astimezone().isoformat()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("zaya visual live proof passed")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"zaya visual live proof failed: {exc}", flush=True)
        sys.exit(1)
