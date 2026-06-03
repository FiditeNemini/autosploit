# Checkpoint 453 - MiniMax Live Continuous Batching

## Goal

Replace the MiniMax continuous-batching readiness placeholder with a real live
loaded-model proof on the low-RAM MiniMax JANGTQ beta target.

## Changes

- Generated `docs/live-proofs/checkpoint-464-minimax-continuous-batching-live.json`.
- Hardened `scripts/prove-live-continuous-batching.py` so failed live runs write
  an artifact with the engine log tail.
- Updated the live proof to accept the engine's explicit MiniMax
  `full_kv_attention` topology label.
- Updated the live proof prompts to exercise enough context for paged/block L2
  cache writes while keeping the model target to the small local MiniMax lane.
- Updated README beta status to move MiniMax live continuous batching from a
  remaining stress gap into the done lane.

## Proof

Verified:

```bash
EXPLOITBOT_LIVE_BATCH_MINIMAX_MODEL=/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ python3 scripts/prove-live-minimax-continuous-batching.py
python3 scripts/minimax-continuous-batching-readiness-proof.py
python3 scripts/continuous-batching-coverage-proof.py
python3 scripts/runtime-coverage-proof.py
```

Live MiniMax artifact metrics:

- `clientOverlap=true`
- `maxNumSeqs=2`
- `max_running_observed=2`
- `max_waiting_observed=2`
- `num_requests_processed=2`
- `total_prompt_tokens=296`
- `total_completion_tokens=32`
- `kv_cache_quantization.bits=4`
- `block_disk_cache.disk_writes=4`
- peak memory about 40.6 GB

The first failed MiniMax run exposed a JANG P18 q/k norm shape bug in the local
JANG loader. The successful proof was rerun after the local loader handled
MiniMax full-width q/k norm separately from per-head q/k norm models.

## Remaining

- This checkpoint proves MiniMax text continuous batching. It does not promote
  the still-blocked Qwen multimodal lane.
