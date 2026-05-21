# Beta Refresh Checkpoint 20 — 2026-05-21

## Scope

Twentieth checkpoint toward the beta-refresh objective:

- Add no-heavy-model coverage for nested model-folder autodetection.
- Keep Qwen wrapper/text-model parser and cache-family detection explicit.

## Changes

- Added a launch test proving `config.json` with a wrapper `model_type` and
  nested `text_config.model_type` still supplies auto parser defaults.
- Added a registry test proving a Qwen wrapper with
  `text_config.model_type=qwen3_next` resolves to the inner Qwen SSM/Mamba
  family for cache metadata while preserving Qwen reasoning/tool parsers.

## Evidence

Passed:

```sh
PYTHONPATH=ExploitBotEngine python3 -m unittest ExploitBotEngine.testsuite.test_launch_model_defaults ExploitBotEngine.testsuite.test_reasoning_registry -v
python3 -m compileall -q ExploitBotEngine
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
PYTHONPATH=ExploitBotEngine /Applications/vMLX.app/Contents/Resources/bundled-python/python/bin/python3 -m unittest discover -s ExploitBotEngine/testsuite -v
scripts/smoke-engine-api.sh
```

System Python ran 19 tests with 3 expected skips for optional runtime packages.
Bundled Python ran all 19 tests successfully. The smoke API reported
`health.status=no_model`, effective cache keys for disk/KV/paged/prefix/SSM,
and `models.count=0`.

## Remaining Proof Gap

This checkpoint proves the no-model autodetection path. It does not prove real
MiniMax or Qwen generation/cache behavior with loaded weights; that remains
gated on freeing enough memory or otherwise reserving a safe model run slot.
