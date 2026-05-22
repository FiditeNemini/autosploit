# Checkpoint 112: Qwen Hybrid Block L2 and SSM Re-Derive Proof

## Scope

- Extend live restart replay verification to Qwen hybrid cache behavior.
- Require explicit SSM re-derive status when a KV block L2 hit cannot be paired
  with a complete SSM companion for the same prefix boundary.

## Changes

- Added `--require-ssm-rederive` to `scripts/verify-live-models.py`.
- Added `_assert_ssm_rederive_behavior()` to fail proofs unless replay cache
  stats show SSM re-derive was requested and completed without failures.
- Added focused unit tests for SSM re-derive proof assertions.

## Proof

Commands:

```bash
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q testsuite/test_live_model_verifier.py
python3 scripts/verify-live-models.py --qwen /Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP --block-l2-only-replay --require-ssm-rederive --timeout 1200 --prompt 'ExploitBot Qwen hybrid block L2 and SSM companion restart replay proof. This prompt is intentionally long enough to create a full paged prefix cache block and a hybrid SSM companion checkpoint before generation. Repeatable context segment alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega. The replay process must disable prompt disk cache and recover cached prefix state from block disk cache plus any SSM companion state. Reply with cache-proof and one short sentence.' --output docs/live-proofs/checkpoint-112-qwen-hybrid-block-l2-ssm-restart-replay-live.json
```

Result:

- Focused verifier tests passed: `16 passed`.
- First process loaded
  `/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP`, disabled prompt L2, wrote
  two block L2 entries, and stored one SSM companion entry at the full prompt
  checkpoint.
- Replay process loaded the same model/cache root with prompt L2 disabled.
- Replay request reported:
  - `block_l2_hits_delta=1`;
  - `scheduler_disk_hits_delta=1`;
  - `scheduler_tokens_saved_delta=64`;
  - `prompt_l2_hits_delta=0`;
  - `prompt_l2_active=false`;
  - `kv_cache_quantization.mode=turboquant-q4`;
  - parser autodetect `reasoning=qwen3`, `tool_call=qwen`;
  - generation defaults from the model folder, including `temperature=1.0`,
    `top_p=0.95`, `top_k=20`.
- SSM companion status reported:
  - `requested=true`;
  - `completed=true`;
  - `reason=missing_companion`;
  - `state=completed`;
  - `no_failures=true`.

Artifact:

- `docs/live-proofs/checkpoint-112-qwen-hybrid-block-l2-ssm-restart-replay-live.json`

## Boundary

This proves live Qwen hybrid KV block L2 replay and the guarded SSM re-derive
path when a companion is missing for the replayed KV prefix. It does not claim a
full hybrid prefix skip from KV plus matching SSM companion, because the replay
hit a 64-token KV block while the stored companion checkpoint was for the longer
prompt boundary.
