# Beta Refresh Checkpoint 21 — 2026-05-21

## Scope

Twenty-first checkpoint toward the beta-refresh objective:

- Strengthen API-visible effective runtime metadata.
- Prove `/health` and `/v1/models` expose the same parser, generation, and
  cache contract without loading a heavy model.

## Changes

- Added `generation.chat_template_kwargs` and
  `generation.custom_chat_template` to `effective_config`.
- Wired those fields from server defaults into `/health.effective_config` and
  `/v1/models[].metadata`.
- Added a bundled-runtime endpoint regression test covering:
  - served model name plus backing model alias in `/v1/models`;
  - reasoning/tool parser metadata;
  - generation defaults including chat-template kwargs;
  - TurboQuant-style KV cache mode metadata;
  - prompt and block L2 disk cache metadata;
  - SSM companion cache metadata.
- Extended `scripts/smoke-engine-api.sh` so the no-model server smoke checks
  the new generation metadata keys.

## Evidence

Passed:

```sh
PYTHONPATH=ExploitBotEngine python3 -m unittest ExploitBotEngine.testsuite.test_runtime_status ExploitBotEngine.testsuite.test_tool_parser_api ExploitBotEngine.testsuite.test_launch_model_defaults ExploitBotEngine.testsuite.test_reasoning_registry -v
python3 -m compileall -q ExploitBotEngine
git diff --check
PYTHONPATH=ExploitBotEngine /Applications/vMLX.app/Contents/Resources/bundled-python/python/bin/python3 -m unittest discover -s ExploitBotEngine/testsuite -v
scripts/smoke-engine-api.sh
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
```

Bundled Python ran all 20 tests successfully. System Python ran 20 tests with
4 expected skips for optional FastAPI/Pydantic server dependencies. The smoke
API reported `health.status=no_model`, effective cache keys for
disk/KV/paged/prefix/SSM, effective generation keys including
`chat_template_kwargs` and `custom_chat_template`, and `models.count=0`.

## Remaining Proof Gap

This checkpoint proves the no-model API metadata contract. It does not prove
real MiniMax or Qwen generation/cache behavior with loaded weights; that
remains gated on freeing enough memory or otherwise reserving a safe model run
slot.
