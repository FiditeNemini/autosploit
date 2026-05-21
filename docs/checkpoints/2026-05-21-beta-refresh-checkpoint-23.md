# Beta Refresh Checkpoint 23 — 2026-05-21

## Scope

Twenty-third checkpoint toward the beta-refresh objective:

- Pin the public reasoning API field contract.
- Keep internal reasoning storage out of serialized OpenAI-compatible payloads.

## Changes

- Added coverage for `AssistantMessage` and `ChatCompletionChunkDelta` proving:
  - internal `reasoning` is excluded from serialized payloads;
  - public `reasoning_content` carries the separated reasoning text;
  - the same contract holds for non-streaming messages and streaming deltas.

## Evidence

Passed:

```sh
PYTHONPATH=ExploitBotEngine python3 -m unittest ExploitBotEngine.testsuite.test_tool_parser_api -v
PYTHONPATH=ExploitBotEngine /Applications/vMLX.app/Contents/Resources/bundled-python/python/bin/python3 -m unittest ExploitBotEngine.testsuite.test_tool_parser_api -v
PYTHONPATH=ExploitBotEngine /Applications/vMLX.app/Contents/Resources/bundled-python/python/bin/python3 -m unittest discover -s ExploitBotEngine/testsuite -v
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
python3 -m compileall -q ExploitBotEngine
git diff --check
scripts/smoke-engine-api.sh
```

Bundled Python ran all 22 tests successfully. System Python ran 22 tests with
6 expected skips for optional FastAPI/Pydantic server dependencies. The smoke
API remained clean in no-model mode.

## Remaining Proof Gap

This checkpoint proves serialization shape only. Real parser behavior still
needs loaded-model generation smoke for MiniMax/Qwen once memory is available.
