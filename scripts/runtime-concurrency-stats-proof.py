#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LLM_SCHEDULER = ROOT / "ExploitBotEngine" / "vmlx_engine" / "scheduler.py"
MLLM_SCHEDULER = ROOT / "ExploitBotEngine" / "vmlx_engine" / "mllm_scheduler.py"
SERVER = ROOT / "ExploitBotEngine" / "vmlx_engine" / "server.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_scheduler(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    label = str(path.relative_to(ROOT))
    for token in (
        "self.max_waiting_observed = 0",
        "self.max_running_observed = 0",
        "self.max_waiting_observed = max(",
        "self.max_running_observed = max(",
        '"max_waiting_observed": self.max_waiting_observed',
        '"max_running_observed": self.max_running_observed',
    ):
        require(token in source, f"{label} missing observed-concurrency token: {token}")


def main() -> None:
    assert_scheduler(LLM_SCHEDULER)
    assert_scheduler(MLLM_SCHEDULER)
    server = SERVER.read_text(encoding="utf-8")
    for token in (
        '"max_waiting_observed": stats.get("max_waiting_observed", 0)',
        '"max_running_observed": stats.get("max_running_observed", 0)',
    ):
        require(token in server, f"server cache stats missing token: {token}")
    print("runtime-concurrency-stats proof passed")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"runtime-concurrency-stats proof failed: {exc}", flush=True)
        raise SystemExit(1)
