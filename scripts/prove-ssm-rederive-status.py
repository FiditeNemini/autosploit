#!/usr/bin/env python3
"""Prove hybrid SSM rederive status is observable without loading a model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "ExploitBotEngine"
sys.path.insert(0, str(ENGINE))

from vmlx_engine.utils.ssm_companion_cache import SSMCompanionCache  # noqa: E402


def prove() -> dict:
    cache = SSMCompanionCache(max_entries=2)

    tokens = [101, 102, 103, 104]
    cache.request_rederive(
        tokens,
        len(tokens),
        reason="missing_companion",
        request_id="proof-ssm",
    )
    queued = cache.rederive_status()

    cache.mark_rederive_completed(
        tokens,
        len(tokens),
        request_id="proof-ssm",
    )
    completed = cache.rederive_status()

    ok = (
        queued["state"] == "queued"
        and queued["reason"] == "missing_companion"
        and queued["queued"] == 1
        and queued["requested"] == 1
        and completed["state"] == "completed"
        and completed["queued"] == 0
        and completed["completed"] == 1
        and completed["last_num_tokens"] == len(tokens)
    )
    return {
        "ok": ok,
        "queued": queued,
        "completed": completed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = prove()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
