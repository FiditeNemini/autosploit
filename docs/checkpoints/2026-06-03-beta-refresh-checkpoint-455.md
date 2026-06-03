# Checkpoint 455 - Responses Streaming Parser Engine Evidence

## Goal

Strengthen the Responses/streaming/parser gate from source-only contract
coverage to route evidence that names the engine tests and parser proof used to
verify the actual reuse and API-shaping paths.

## Changes

- Updated `/qa/streaming-parser-reuse.proofLevel` to
  `app-source-and-engine-test-backed`.
- Added engine test evidence fields to `/qa/streaming-parser-reuse`:
  `engineTestFiles`, `engineTestFileParity`, `engineTestCommands`, and
  `engineTestCommandCount`.
- Added contracts for Responses session-store engine tests and parser API shape
  proof.
- Updated runtime/deep-runtime proofs so aggregate gates require the stronger
  proof level.
- Updated README/runtime checkpoint wording for the stronger gate.

## Proof

Verified:

```bash
python3 scripts/streaming-parser-reuse-proof.py
cd ExploitBotEngine && PYTHONPATH=. .venv/bin/python -m pytest -q testsuite/test_responses_session_store.py testsuite/test_tool_parser_api.py
ExploitBotEngine/.venv/bin/python scripts/prove-parser-api.py
```

The engine tests prove:

- stored Responses turns rehydrate `previous_response_id` context;
- new Responses sessions do not replay old context;
- child and grandchild continuations preserve full ancestor context;
- parser output uses API-shaped `reasoning_content`, `tool_calls`, and
  `finish_reason=tool_calls`.

## Remaining

- This is not a live loaded-model streaming prompt suite. Live chat/cache
  evidence stays in the Qwen/MiniMax live artifacts, while broader realistic
  chat/tool-call quality remains a follow-up gate.
