# Checkpoint 80 - Strict MiniMax Live Gate

## Scope

- Rerun MiniMax JANGTQ live verification after memory pressure cleared.
- Fix the live verifier so token usage alone is not accepted as generation
  proof when the assistant message is empty.
- Record the current MiniMax state honestly.

## Changes

- `scripts/verify-live-models.py` now rejects completions that report generated
  tokens but return no assistant `content`, `reasoning_content`, or
  `tool_calls`.
- Added regression coverage in `testsuite/test_live_model_verifier.py` for
  token-usage-with-empty-message false positives.
- The verifier now stores health, model, completion preview, usage, and cache
  stats before assertion failures so failed live reports still carry useful
  evidence.

## Proof

- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q testsuite/test_live_model_verifier.py`
- `cd ExploitBotEngine && uv run --extra dev ../scripts/verify-live-models.py --minimax /Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ --output ../docs/live-proofs/checkpoint-80-minimax-strict-live.json --timeout 900`

The MiniMax live run now gets past the previous OOM:

- model loads through `jang_tools.load_jangtq_model`;
- warmup succeeds;
- `/health`, `/v1/models`, and `/v1/cache/stats` respond;
- runtime metadata proves full-KV topology, prefix cache, prompt L2, paged
  cache, block L2, and TurboQuant Q4;
- cache counters show reuse (`scheduler_cache.hits=1`,
  `scheduler_cache.tokens_saved=52`);
- prompt cached usage is reported (`cached_tokens=51` then `52`).

The run is still **not** a generation pass:

- `ok=false`;
- both first and repeat responses return
  `content=null`, `tool_calls=null`, and `reasoning_content=null`;
- both responses finish with `finish_reason=length`;
- the verifier fails with `empty assistant message: token usage reported
  without content/reasoning/tool_calls`.

## Remaining

- MiniMax no longer appears blocked by memory pressure, but the live generation
  payload is empty. The next MiniMax task is to debug why the JANGTQ decode path
  emits token usage without API-visible text/reasoning/tool-call output.
