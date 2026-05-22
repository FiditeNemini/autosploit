# Checkpoint 77 - Quantized Block L2 Write-Through And Promotion

## Scope

- Prove block L2 disk cache behavior for quantized KV cache blocks.
- Make the block-aware prefix cache write quantized KV blocks to disk when the
  non-quantized numpy slice path is unavailable.
- Make prefix-cache fetch use chain-hash L2 promotion for full cached blocks.

## Changes

- `BlockAwarePrefixCache.store_cache()` now queues direct write-through for
  extracted block cache data when `np_sources` is empty. This covers
  `("quantized_kv", ...)` block data emitted by TurboQuant-style cache slices.
- `BlockAwarePrefixCache.fetch_cache()` now calls
  `PagedCacheManager.get_computed_blocks()` after the legacy in-memory prefix
  lookup misses, allowing full blocks to be promoted from block L2 disk cache.
- `BlockDiskStore` now stores its serialized layer metadata under
  `vmlx_block_metadata` instead of `__metadata__`. MLX/safetensors treats the
  old key specially and rejected those files at load time.
- Added `scripts/prove-block-l2-cache.py`, a lightweight proof that writes a
  real MLX quantized KV block to `BlockDiskStore`, reopens the store, and
  verifies prefix fetch promotes the block from disk.

## Proof

- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q testsuite/test_disk_cache_manager.py`
- `cd ExploitBotEngine && uv run --extra dev ../scripts/prove-block-l2-cache.py --output ../docs/live-proofs/checkpoint-77-block-l2-quantized-proof.json`

The proof report shows:

- `ok=true`
- `write_stats.disk_writes=1`
- `write_stats.blocks_on_disk=1`
- `paged_stats.disk_hits=1`
- `promoted_block.type=quantized_kv`
- `promoted_table.num_tokens=4`
- `promoted_table.remaining=[]`

## Remaining

- This is a direct cache proof, not a full model-generation proof.
- MiniMax still needs a clear-memory live run to prove full KV attention,
  TurboQuant cache encode/decode, and L2 hits under the actual model path.
- Qwen live proof already shows repeated-prompt in-memory prefix reuse and SSM
  companion storage; async rederive and cross-run disk hit proof remain open.
