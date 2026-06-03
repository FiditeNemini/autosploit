# Beta Refresh Checkpoint 470 - Streamed Responses Session Store

Date: 2026-06-03

## Goal

Close a runtime gap in streamed `/v1/responses`: a streamed parent response with
`store=true` must be replayable by a later streamed request using
`previous_response_id`, while preserving streamed content, reasoning, and parsed
tool-call delta evidence.

## Changes

- Added an engine regression covering streamed Responses session replay.
- Updated `stream_responses_api` to call `store_response_session` before
  emitting `response.completed` when `request.store` is true.
- Extended `/qa/streaming-parser-reuse` and
  `/qa/engine-api-cache-proof-matrix` with a source-backed
  `responsesStreamingSessionStore` contract.
- Updated the README beta lane with streamed Responses session reuse.

## Proof

Red path:

- `cd ExploitBotEngine && PYTHONPATH=. .venv/bin/python -m pytest -q testsuite/test_responses_session_store.py`
- Expected failure before the engine fix:
  `previous_response_id not found` for a streamed parent response id.

Green path:

- `cd ExploitBotEngine && PYTHONPATH=. .venv/bin/python -m pytest -q testsuite/test_responses_session_store.py`
- `python3 scripts/engine-api-cache-proof-matrix-proof.py`

The regression proves streamed `response.reasoning.delta`,
`response.output_text.delta`, and `response.function_call_arguments.delta`
events, then reuses the streamed parent id as `previous_response_id` and verifies
the second engine call carries parent text plus the parsed assistant tool call.

## Remaining

This checkpoint closes streamed Responses session-store replay. It does not
close the tracked Qwen multimodal runtime promotion, multimodal prefix-cache, or
multimodal context-routing live-proof gaps.
