#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCH = ROOT / "ExploitBotEngine" / "launch.py"
SERVER = ROOT / "ExploitBotEngine" / "vmlx_engine" / "server.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    launch = LAUNCH.read_text(encoding="utf-8")
    server = SERVER.read_text(encoding="utf-8")

    for token in (
        '"--max-num-seqs"',
        'kwargs.get("max_num_seqs", 2)',
        'max_num_seqs=args.max_num_seqs',
    ):
        require(token in launch, f"launch.py missing continuous batching CLI token: {token}")

    for token in (
        '"--max-num-seqs"',
        'max_num_seqs=getattr(args, "max_num_seqs", 1)',
    ):
        require(token in server, f"server.py missing continuous batching CLI token: {token}")

    print("runtime-continuous-batching-cli proof passed")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"runtime-continuous-batching-cli proof failed: {exc}", flush=True)
        raise SystemExit(1)
