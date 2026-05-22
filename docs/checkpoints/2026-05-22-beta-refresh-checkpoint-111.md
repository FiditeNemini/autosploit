# Checkpoint 111: MiniMax Block L2 Restart Replay Proof

## Scope

- Add a verifier path that proves block L2 independently from prompt L2.
- Run MiniMax with prompt disk cache disabled so restart replay must use the
  paged block disk cache.

## Changes

- Added `build_live_engine_command()` to `scripts/verify-live-models.py` so live
  proof commands can explicitly disable prompt L2 while keeping prefix cache,
  paged cache, block L2, and TurboQuant enabled.
- Added `--block-l2-only-replay` to the live verifier.
- Restart replay assertions can now require a cross-process block L2 disk-hit
  counter increment.
- Added a unit test proving the generated live command disables prompt L2 and
  keeps block L2 enabled.

## Proof

Commands:

```bash
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q testsuite/test_live_model_verifier.py
python3 scripts/verify-live-models.py --minimax /Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ --block-l2-only-replay --timeout 1200 --prompt 'ExploitBot block L2 restart replay proof. This prompt is intentionally long enough to create at least one full paged prefix cache block before generation. Repeatable context segment alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega. The replay process must disable prompt disk cache and recover cached prefix state from block disk cache only. Reply with cache-proof and one short sentence.' --output docs/live-proofs/checkpoint-111-minimax-block-l2-restart-replay-live.json
```

Result:

- Focused verifier tests passed: `14 passed`.
- First process loaded
  `/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ` with prompt L2 disabled
  and wrote two block L2 entries.
- Replay process loaded the same model and block cache root with prompt L2 still
  disabled.
- Replay request reported:
  - `prompt_tokens_details.cached_tokens=64`;
  - `block_disk_cache.disk_hits=1`;
  - `scheduler_cache.disk_hits=1`;
  - `scheduler_cache.tokens_saved=64`;
  - `restart_replay_cache_checks.block_l2_hits_delta=1`;
  - `restart_replay_cache_checks.prompt_l2_hits_delta=0`.
- Effective config showed full KV attention with prefix cache, paged cache,
  block L2, and TurboQuant Q4 enabled while `prompt_l2_active=false`.

Artifact:

- `docs/live-proofs/checkpoint-111-minimax-block-l2-restart-replay-live.json`

## Boundary

This proves real MiniMax cross-process block L2 replay. It does not cover Qwen
hybrid SSM companion restore or async rederive execution.
