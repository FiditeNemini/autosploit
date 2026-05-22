# Checkpoint 102 - Partial Block L2 Promotion

## Scope

- Prove block L2 disk promotion for final partial quantized KV blocks.
- Keep the existing full-block proof intact.

## Changes

- `PagedCacheManager.get_computed_blocks()` now checks the final short block
  against `BlockDiskStore` after preceding full blocks match.
- `scripts/prove-block-l2-cache.py` now writes and reopens both:
  - a full 4-token quantized KV block;
  - a 3-token final partial quantized KV block.
- Proof artifact:
  `docs/live-proofs/checkpoint-102-block-l2-partial-proof.json`.

## Verification

- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q testsuite/test_disk_cache_manager.py`
- `cd ExploitBotEngine && uv run --extra dev ../scripts/prove-block-l2-cache.py --output ../docs/live-proofs/checkpoint-102-block-l2-partial-proof.json`

## Evidence

- `write_stats.disk_writes=2`
- `write_stats.blocks_on_disk=2`
- `paged_stats.disk_hits=2`
- `promoted_full_block.type=quantized_kv`
- `promoted_full_block.token_count=4`
- `promoted_partial_block.type=quantized_kv`
- `promoted_partial_block.token_count=3`
- `promoted_full_table.remaining=[]`
- `promoted_partial_table.remaining=[]`

## Remaining

- This is a direct cache proof, not a real-model restart/replay proof.
- Qwen hybrid async SSM rederive status remains a separate open lane.
