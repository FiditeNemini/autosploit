# Checkpoint 454 - Qwen and MiniMax Live Batching Gate

## Goal

Promote MiniMax continuous batching from an advisory readiness row to a required
live-artifact contract alongside the existing Qwen live batching proof.

## Changes

- Updated `/qa/continuous-batching-coverage` so the green proof level is
  `source-and-live-qwen-minimax-stress-backed` only when both Qwen and MiniMax
  live batching artifacts are valid.
- Added `qwenLiveLoadedModelStress` and `minimaxLiveLoadedModelStress` to the
  continuous-batching contract map.
- Mirrored the MiniMax live batching requirement through
  `/qa/runtime-coverage`, `/qa/deep-runtime-flow-coverage`, and
  `/qa/coverage-index`.
- Tightened MiniMax readiness, continuous-batching, runtime, deep-runtime, and
  app QA proof scripts so missing MiniMax live concurrency/cache evidence fails
  the gate.
- Updated checkpoint and README wording so MiniMax live batching is no longer
  described as pending.

## Proof

Verified:

```bash
python3 scripts/continuous-batching-coverage-proof.py
```

Required live artifact:

- `docs/live-proofs/checkpoint-464-minimax-continuous-batching-live.json`

MiniMax live counters:

- `clientOverlap=true`
- `max_running_observed=2`
- `max_waiting_observed=2`
- `num_requests_processed=2`
- `kv_cache_quantization.bits=4`
- `block_disk_cache.disk_writes=4`

## Remaining

- Higher-cardinality batching and loaded-model multi-agent stress are still
  separate follow-up gates.
