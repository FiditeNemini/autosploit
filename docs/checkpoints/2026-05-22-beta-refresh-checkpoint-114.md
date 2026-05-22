# Checkpoint 114: MiniMax No-Thinking API Proof

## Scope

- Add explicit live-verifier control for per-request thinking mode.
- Fix non-streaming chat response shaping so forced reasoning-off MiniMax
  requests cannot turn generated tokens into an empty assistant message.
- Prove the real MiniMax model returns API-visible content with
  `enable_thinking=false` while preserving cache/parser/runtime metadata.

## Changes

- Added `--enable-thinking auto|true|false` to `scripts/verify-live-models.py`.
- The live verifier now records the selected smoke thinking mode and uses it in
  normal, populate, and replay completion requests.
- Added `_content_when_reasoning_suppressed()` in `vmlx_engine.server`.
- Non-streaming chat now skips reasoning extraction when thinking is explicitly
  disabled and returns sanitized visible text instead of suppressing it into an
  empty assistant message.
- Added focused tests for thinking-mode resolution and suppressed-reasoning
  content shaping.

## Proof

Commands:

```bash
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q testsuite/test_tool_parser_api.py::ToolParserApiTests::test_reasoning_suppressed_text_does_not_become_empty_content testsuite/test_live_model_verifier.py::LiveModelVerifierTests::test_smoke_thinking_mode_supports_auto_and_explicit_override
python3 scripts/verify-live-models.py --minimax /Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ --enable-thinking false --timeout 1200 --prompt 'ExploitBot MiniMax no-thinking smoke. Reply with cache-proof and one short sentence.' --output docs/live-proofs/checkpoint-114-minimax-no-thinking-live.json
```

Result:

- Focused tests passed: `2 passed`.
- Live proof loaded `/Users/eric/models/JANGQ/MiniMax-M2.7-Small-JANGTQ`.
- Request proof recorded `smoke_enable_thinking=false` and
  `smoke_enable_thinking_mode=false`.
- Assistant response had non-empty `content` and no `reasoning_content`.
- Runtime metadata showed MiniMax parser autodetect (`minimax_m2` reasoning,
  `minimax` tool parser), model-folder generation defaults, TurboQuant Q4 KV,
  prefix cache, prompt L2, paged cache, and block L2.
- Repeat prompt reuse reported `cached_tokens=51`,
  `scheduler_cache_hits_delta=1`, and `scheduler_tokens_saved_delta=51`.

Artifact:

- `docs/live-proofs/checkpoint-114-minimax-no-thinking-live.json`

## Boundary

This proves API response shaping and cache reuse for MiniMax when a caller
forces thinking off. It does not evaluate answer quality under the verifier's
tiny `max_tokens=16` cap.
