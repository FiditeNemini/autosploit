#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP"
DEFAULT_OUTPUT = ROOT / "docs" / "live-proofs" / "checkpoint-465-qwen-continuous-batching-4-live.json"


def main() -> int:
    env = os.environ.copy()
    env["EXPLOITBOT_LIVE_BATCH_FAMILY"] = "qwen"
    env["EXPLOITBOT_LIVE_BATCH_MAX_NUM_SEQS"] = "4"
    env.setdefault("EXPLOITBOT_LIVE_BATCH_MODEL", env.get("EXPLOITBOT_LIVE_BATCH_QWEN_MODEL", DEFAULT_MODEL))
    env.setdefault("EXPLOITBOT_LIVE_BATCH_OUTPUT", str(DEFAULT_OUTPUT))
    return subprocess.call([sys.executable, str(ROOT / "scripts" / "prove-live-continuous-batching.py")], cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
