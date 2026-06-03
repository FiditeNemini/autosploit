# Checkpoint 457 - Qwen 4-Way Live Batching Stress

## Goal

Promote Qwen live continuous batching beyond the initial two-request proof while
staying on the smallest local Qwen beta target to keep RAM pressure controlled.

## Changes

- Made `scripts/prove-live-continuous-batching.py` configurable through
  `EXPLOITBOT_LIVE_BATCH_MAX_NUM_SEQS`.
- Added `scripts/prove-live-qwen-continuous-batching-4.py`, which defaults to
  `/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP` and writes
  `docs/live-proofs/checkpoint-465-qwen-continuous-batching-4-live.json`.
- Updated `/qa/continuous-batching-coverage`,
  `/qa/session-context-cache-flow`, `/qa/runtime-coverage`,
  `/qa/deep-runtime-flow-coverage`, and `/qa/coverage-index` to require and
  mirror the Qwen 4-way artifact.
- Updated README and runtime checkpoint docs so the beta lane names the stronger
  proof level:
  `source-and-live-qwen-minimax-plus-qwen-4way-stress-backed`.

## Proof

Live command:

```bash
EXPLOITBOT_LIVE_BATCH_QWEN_MODEL=/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP python3 scripts/prove-live-qwen-continuous-batching-4.py
```

Recorded in `docs/live-proofs/checkpoint-465-qwen-continuous-batching-4-live.json`:

- `clientOverlap=true`
- `maxNumSeqs=4`
- `max_running_observed=4`
- `max_waiting_observed=4`
- `num_requests_processed=4`
- `kv_cache_quantization.bits=4`
- `block_disk_cache.disk_writes=5`
- `ssm_companion.rederive.completed=4`
- `ssm_companion.rederive.failed=0`
- `memory.active_mb=14671.1`

## Remaining

- Loaded-model multi-agent stress remains a separate gate.
