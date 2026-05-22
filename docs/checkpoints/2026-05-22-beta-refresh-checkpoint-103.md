# Checkpoint 103 - Hybrid SSM Re-Derive Status

## Scope

- Make hybrid SSM companion re-derive state visible in backend cache stats.
- Carry the same status through the Swift app cache parser and Settings Engine
  summary.

## Changes

- `SSMCompanionCache` now records re-derive status:
  `idle`, `queued`, `running`, `completed`, and `failed`.
- The scheduler records a queued re-derive request when a hybrid KV prefix hit
  cannot be used because companion SSM state is missing or incomplete.
- Fallback full-prefill companion storage marks the re-derive status completed;
  SSM companion store errors mark it failed.
- `/v1/cache/stats` includes `ssm_companion.rederive`.
- `EngineCacheStats` parses the status and `/state.engineCacheStats` exposes
  the counters.
- Settings Engine shows an `SSM ReDerive` runtime row.

## Verification

- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q testsuite/test_hybrid_ssm_helpers.py -k "rederive or scheduler_ssm"`
- `cd ExploitBotEngine && uv run --extra dev ../scripts/prove-ssm-rederive-status.py --output ../docs/live-proofs/checkpoint-103-ssm-rederive-status-proof.json`
- `python3 scripts/cache-stats-state-proof.py`

## Evidence

- `queued.state=queued`
- `queued.reason=missing_companion`
- `queued.queued=1`
- `queued.requested=1`
- `completed.state=completed`
- `completed.completed=1`
- `/state.engineCacheStats.ssmReDeriveState=queued`
- `/state.engineCacheStats.ssmReDeriveQueued=2`

## Remaining

- This proves visible status and fallback accounting, not true background
  re-derive execution under a loaded Qwen hybrid model.
