# Checkpoint 79 - Parser API Proof

## Scope

- Prove mixed reasoning and tool-call model output is exposed through API-safe
  fields.
- Cover the user requirement that reasoning parser and tool parser output is
  autodetected/configured and API-shaped instead of left as raw tags.

## Changes

- Added a regression in `testsuite/test_tool_parser_api.py` for one mixed Qwen
  output containing both `<think>...</think>` reasoning and a Qwen
  `<tool_call>...</tool_call>` block.
- Added `scripts/prove-parser-api.py`, which configures the server helper path
  with `reasoning=qwen3`, `tool_call=qwen`, and auto tool choice enabled, then
  writes a JSON proof artifact.

## Proof

- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q testsuite/test_tool_parser_api.py`
- `cd ExploitBotEngine && uv run --extra dev ../scripts/prove-parser-api.py --output ../docs/live-proofs/checkpoint-79-parser-api-proof.json`

The proof report shows:

- `ok=true`
- configured parser metadata: `reasoning=qwen3`, `tool_call=qwen`,
  `auto_tool_choice=true`
- assistant content is cleaned to `Ready.`
- `reasoning_content` contains the thinking text
- `tool_calls[0].function.name=run_shell`
- `finish_reason=tool_calls`
- raw `<think>` and `<tool_call>` tags are not present in assistant content

## Remaining

- This proves the API parser shaping path without loading a model. Real-model
  generation still depends on the Qwen/MiniMax live proof gates.
