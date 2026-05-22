# Checkpoint 122 - engine no-model metadata proof

## Scope

- Add a repeatable proof that the Python engine reports effective runtime
  metadata even when no model is loaded.
- Surface the cache-response inference contract used by long-context sessions.

## Changes

- Added `scripts/engine-no-model-metadata-proof.py`.
  - Builds a temporary Qwen hybrid fixture.
  - Forces no-model engine state.
  - Verifies `/health` reports `status=no_model` without claiming load success.
  - Verifies `/health.effective_config` and `/v1/models[].metadata` agree.
  - Checks reasoning/tool parser autodetect, generation defaults/provenance,
    hybrid SSM topology, prefix cache, prompt L2, paged cache, block L2,
    TurboQuant Q4, SSM companion L2, and all expected topology components.
- Added `cache.responses` metadata in
  `ExploitBotEngine/vmlx_engine/runtime_status.py`:
  - `method=prefix-cache-l2-turboquant` when prefix cache, L2 cache, and
    TurboQuant KV are active;
  - `prefix_cache_required=true`;
  - `new_context_preserves_engine_session=true`;
  - `clears_conversation_state_only=true`.
- Extended `testsuite/test_runtime_status.py` to keep the cache-response
  contract covered in unit tests.
- Updated the app review/inventory docs to mark the engine no-model metadata
  gate covered.

## Verification

- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev ../scripts/engine-no-model-metadata-proof.py`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q testsuite/test_runtime_status.py testsuite/test_server_cache_defaults.py testsuite/test_launch_model_defaults.py`

## Notes

- This is a no-model metadata proof. It does not replace real Qwen/MiniMax
  generation, cache-hit, TurboQuant encode/decode, or SSM rederive proofs.
