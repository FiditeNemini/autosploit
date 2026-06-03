# Checkpoint 458 - Live Loaded-Model Agent Stress

## Goal

Close the remaining gap between app-side parallel-agent proof and engine-side
live batching proof by driving two app-managed agents against a real loaded Qwen
engine.

## Changes

- Added `scripts/prove-live-loaded-model-agent-stress.py`, which live-loads
  `/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP`, points two app agents at the
  loaded engine, and writes
  `docs/live-proofs/checkpoint-466-qwen-live-agent-stress.json`.
- Added `/qa/live-loaded-model-agent-stress` and mirrored it through
  `/qa/runtime-coverage`, `/qa/deep-runtime-flow-coverage`,
  `/qa/session-context-cache-flow`, `/qa/objective-runtime-coverage`, and
  `/qa/coverage-index`.
- Fixed `ChatService` request construction so bounded selected context is merged
  into the first system message instead of appended as a later system message,
  which Qwen chat templates reject.
- Tightened route, runtime, deep-runtime, session/cache, objective, coverage
  index, and app smoke proofs so missing live loaded-model agent stress evidence
  fails.

## Proof

Live command:

```bash
EXPLOITBOT_LIVE_AGENT_QWEN_MODEL=/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP python3 scripts/prove-live-loaded-model-agent-stress.py
```

Recorded in `docs/live-proofs/checkpoint-466-qwen-live-agent-stress.json`:

- `appMaxWorkingObserved=2`
- `max_running_observed=2`
- `num_requests_processed=2`
- `kv_cache_quantization.bits=4`
- `block_disk_cache.disk_writes=181`
- `ssm_companion.rederive.completed=2`
- `ssm_companion.rederive.failed=0`
- `memory.active_mb=14426.2`
- `memory.peak_mb=18649.8`

## Remaining

- Qwen multimodal runtime promotion remains separate from this text-agent stress
  lane.
