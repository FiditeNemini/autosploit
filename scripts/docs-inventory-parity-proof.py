#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYSTEM_REVIEW = ROOT / "docs" / "app-system-review-2026-05-21.md"
FLOW_INVENTORY = ROOT / "docs" / "app-flow-inventory-2026-05-21.md"

REQUIRED_QWEN_PROMOTION_TERMS = [
    "promotion gates",
    "Qwen multimodal loader",
    "multimodal prefix-cache key discipline",
    "multimodal context packet routing",
    "promotion remains false",
    "live-qwen-multimodal-loader-proof.py",
    "live-qwen-multimodal-prefix-cache-proof.py",
    "live-qwen-multimodal-context-routing-proof.py",
]


def assert_doc(path: Path) -> None:
    text = " ".join(path.read_text(encoding="utf-8").split())
    missing = [term for term in REQUIRED_QWEN_PROMOTION_TERMS if term not in text]
    if missing:
        raise AssertionError(f"{path.relative_to(ROOT)} missing Qwen promotion terms: {missing}")


def run() -> None:
    assert_doc(SYSTEM_REVIEW)
    assert_doc(FLOW_INVENTORY)
    print("docs-inventory-parity proof passed")


if __name__ == "__main__":
    try:
        run()
    except AssertionError as exc:
        print(f"docs-inventory-parity proof failed: {exc}", flush=True)
        raise SystemExit(1)
