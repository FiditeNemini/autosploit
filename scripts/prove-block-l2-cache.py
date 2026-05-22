#!/usr/bin/env python3
"""Prove block L2 cache write-through and disk promotion without loading a model."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "ExploitBotEngine"
sys.path.insert(0, str(ENGINE))

import mlx.core as mx  # noqa: E402

from vmlx_engine.block_disk_store import BlockDiskStore  # noqa: E402
from vmlx_engine.paged_cache import PagedCacheManager  # noqa: E402
from vmlx_engine.prefix_cache import BlockAwarePrefixCache  # noqa: E402


def _quantized_state(num_tokens: int):
    shape = (1, 1, num_tokens, 4)
    data = mx.arange(num_tokens * 4, dtype=mx.int32).reshape(shape)
    scales = mx.ones(shape, dtype=mx.float16)
    zeros = mx.zeros(shape, dtype=mx.float16)
    return (data, scales, zeros)


def _wait_for_disk_write(store: BlockDiskStore, timeout_s: float = 5.0) -> dict:
    deadline = time.time() + timeout_s
    stats = store.get_stats()
    while time.time() < deadline:
        stats = store.get_stats()
        if stats.get("disk_writes", 0) > 0 and stats.get("blocks_on_disk", 0) > 0:
            return stats
        time.sleep(0.05)
    return stats


def prove(cache_dir: Path) -> dict:
    tokens = [101, 102, 103, 104]
    key_state = _quantized_state(len(tokens))
    value_state = _quantized_state(len(tokens))

    first_store = BlockDiskStore(str(cache_dir), max_size_gb=0.001)
    try:
        first_paged = PagedCacheManager(
            block_size=4,
            max_blocks=8,
            disk_store=first_store,
        )
        first_prefix = BlockAwarePrefixCache(
            model=object(),
            paged_cache_manager=first_paged,
        )
        first_table = first_prefix.store_cache(
            "proof-store",
            tokens,
            [
                {
                    "class_name": "QuantizedKVCache",
                    "state": (key_state, value_state),
                    "meta_state": {"bits": 4, "group_size": 64},
                }
            ],
        )
        write_stats = _wait_for_disk_write(first_store)
    finally:
        first_store.shutdown()

    second_store = BlockDiskStore(str(cache_dir), max_size_gb=0.001)
    try:
        second_paged = PagedCacheManager(
            block_size=4,
            max_blocks=8,
            disk_store=second_store,
        )
        second_prefix = BlockAwarePrefixCache(
            model=object(),
            paged_cache_manager=second_paged,
        )
        promoted_table, remaining = second_prefix.fetch_cache("proof-fetch", tokens)
        read_stats = second_store.get_stats()

        promoted_block = None
        if promoted_table and promoted_table.block_ids:
            promoted_block = second_paged.allocated_blocks.get(promoted_table.block_ids[0])
        promoted_type = None
        promoted_tokens = None
        if promoted_block and promoted_block.cache_data:
            promoted_type = promoted_block.cache_data[0][0]
            promoted_tokens = promoted_block.token_count

        result = {
            "ok": bool(
                first_table
                and write_stats.get("disk_writes", 0) > 0
                and write_stats.get("blocks_on_disk", 0) > 0
                and promoted_table
                and remaining == []
                and second_paged.stats.disk_hits == 1
                and promoted_type == "quantized_kv"
            ),
            "stored_tokens": first_table.num_tokens if first_table else 0,
            "write_stats": write_stats,
            "promoted_table": {
                "block_ids": promoted_table.block_ids if promoted_table else [],
                "num_tokens": promoted_table.num_tokens if promoted_table else 0,
                "remaining": remaining,
            },
            "paged_stats": {
                "cache_hits": second_paged.stats.cache_hits,
                "cache_misses": second_paged.stats.cache_misses,
                "disk_hits": second_paged.stats.disk_hits,
                "disk_misses": second_paged.stats.disk_misses,
            },
            "read_stats": read_stats,
            "promoted_block": {
                "type": promoted_type,
                "token_count": promoted_tokens,
            },
        }
    finally:
        second_store.shutdown()

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()

    temp_dir = None
    if args.cache_dir is None:
        temp_dir = tempfile.mkdtemp(prefix="vmlx-block-l2-proof-")
        cache_dir = Path(temp_dir)
    else:
        cache_dir = args.cache_dir
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True)

    try:
        result = prove(cache_dir)
        result["cache_dir"] = "temporary" if temp_dir is not None else str(cache_dir)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
