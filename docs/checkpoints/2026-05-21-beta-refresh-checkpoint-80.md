# Checkpoint 80 - Strict MiniMax Live Gate

## Scope

- Rerun MiniMax JANGTQ live verification after memory pressure cleared.
- Fix the live verifier so token usage alone is not accepted as generation
  proof when the assistant message is empty.
- Prove the working MiniMax live path with isolated proof caches and repeat
  prefix-cache reuse.

## Changes

- `scripts/verify-live-models.py` now rejects completions that report generated
  tokens but return no assistant `content`, `reasoning_content`, or
  `tool_calls`.
- MiniMax live smoke requests now use thinking-enabled template kwargs. Manual
  isolation showed MiniMax can return API-visible text with thinking enabled,
  while forced no-thinking requests can report token usage with an empty
  assistant payload.
- Live verifier runs now use temporary prompt/block L2 cache directories so a
  stale persistent cache entry cannot make the proof pass or fail for the wrong
  reason.
- Added regression coverage in `testsuite/test_live_model_verifier.py` for
  token-usage-with-empty-message false positives and isolated cache launch
  arguments.
- The verifier stores completion preview, usage, and cache stats before
  completion assertions so failed live reports still carry useful evidence.

## Proof

- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q testsuite/test_live_model_verifier.py`
- `cd ExploitBotEngine && uv run --extra dev ../scripts/verify-live-models.py --minimax /Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ --output ../docs/live-proofs/checkpoint-80-minimax-strict-live.json --timeout 900 --prompt 'Say hello in exactly three words.'`

The MiniMax live run now passes:

- model loads through `jang_tools.load_jangtq_model`;
- warmup succeeds;
- `/health`, `/v1/models`, and `/v1/cache/stats` respond;
- runtime metadata proves full-KV topology, prefix cache, prompt L2, paged
  cache, block L2, and TurboQuant Q4;
- first and repeat responses return non-empty assistant `content`;
- repeat prompt usage reports `cached_tokens=40`;
- cache counters show reuse (`scheduler_cache.hits_delta=1`,
  `scheduler_cache.tokens_saved_delta=40`);
- temporary prompt/block cache directories are visible in `/health`,
  `/v1/models`, and the engine log.

## Remaining

- This is a functional generation/cache proof, not a quality proof. The prompt
  is intentionally short and the response is length-capped at 16 generated
  tokens.
- Forced no-thinking MiniMax requests still need separate investigation before
  being exposed as a guaranteed mode.
