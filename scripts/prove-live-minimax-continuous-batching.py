#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ"
DEFAULT_OUTPUT = ROOT / "docs" / "live-proofs" / "checkpoint-464-minimax-continuous-batching-live.json"


def main() -> int:
    env = os.environ.copy()
    env["EXPLOITBOT_LIVE_BATCH_FAMILY"] = "minimax"
    env.setdefault("EXPLOITBOT_LIVE_BATCH_MODEL", env.get("EXPLOITBOT_LIVE_BATCH_MINIMAX_MODEL", DEFAULT_MODEL))
    env.setdefault("EXPLOITBOT_LIVE_BATCH_OUTPUT", str(DEFAULT_OUTPUT))
    return subprocess.call([sys.executable, str(ROOT / "scripts" / "prove-live-continuous-batching.py")], cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
