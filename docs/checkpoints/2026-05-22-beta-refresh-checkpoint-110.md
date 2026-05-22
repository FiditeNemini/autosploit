# Checkpoint 110: MiniMax Restart Replay Cache Proof

## Scope

- Add a live verifier mode for cross-process cache replay.
- Prove MiniMax can populate prefix/prompt L2 cache, restart the engine against
  the same cache root, and reuse cached prompt tokens on the replay request.

## Changes

- Added `--restart-replay` to `scripts/verify-live-models.py`.
- The verifier now runs two engine processes against one isolated cache root:
  - first run populates prompt L2 and block L2 cache roots;
  - second run reloads the same model and cache roots;
  - replay request must show cached-token evidence or an L2 disk-hit counter.
- Added restart replay assertions to
  `ExploitBotEngine/testsuite/test_live_model_verifier.py`.

## Proof

Commands:

```bash
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q testsuite/test_live_model_verifier.py
python3 scripts/verify-live-models.py --minimax /Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ --metadata-only --restart-replay --output docs/live-proofs/checkpoint-110-minimax-restart-replay-metadata.json
python3 scripts/verify-live-models.py --minimax /Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ --restart-replay --timeout 1200 --prompt 'ExploitBot restart replay proof. Reply with the word cache-proof and one short sentence.' --output docs/live-proofs/checkpoint-110-minimax-restart-replay-live.json
```

Result:

- Focused verifier tests passed: `13 passed`.
- Metadata proof shows MiniMax generation defaults loaded from the model folder:
  `temperature=1.0`, `top_p=0.95`, `top_k=40`, with parser autodetect resolving
  `reasoning=minimax_m2` and `tool_call=minimax`.
- Live proof loaded
  `/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ` twice.
- First process wrote one prompt L2 entry and one block L2 entry.
- Replay process started with existing cache entries, then reported:
  - `prompt_tokens_details.cached_tokens=55`;
  - `disk_cache.hits=1`;
  - `restart_replay_cache_checks.prompt_l2_hits_delta=1`;
  - `restart_replay_cache_checks.cached_usage=true`;
  - full KV attention topology with prefix cache, prompt L2, paged cache,
    block L2, and TurboQuant Q4 enabled.

Artifacts:

- `docs/live-proofs/checkpoint-110-minimax-restart-replay-metadata.json`
- `docs/live-proofs/checkpoint-110-minimax-restart-replay-live.json`

## Boundary

This proves real MiniMax cross-process prompt L2 replay and cached-token reuse.
The same run showed block L2 writes/persistence, but the replay request was
satisfied by prompt L2, so it is not claimed as a real-model block-L2 hit proof.
