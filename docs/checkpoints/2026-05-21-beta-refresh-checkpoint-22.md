# Beta Refresh Checkpoint 22 — 2026-05-21

## Scope

Twenty-second checkpoint toward the beta-refresh objective:

- Make cache stats recognize current TurboQuant cache factories.
- Surface hybrid TurboQuant attention/SSM companion metadata for debugging
  Qwen-style hybrid runs.

## Changes

- Updated `/v1/cache/stats` TurboQuant detection to use the current
  `is_turboquant_make_cache` helper.
- Kept a fallback for all known wrapper names:
  `_tq_make_cache`, `_turboquant_make_cache`, and
  `_hybrid_turboquant_make_cache`.
- Added cache-stats metadata for hybrid TurboQuant wrappers:
  `hybrid_policy`, `attention_layers`, and `companion_layers`.
- Added a bundled-runtime fake-engine regression test proving
  `_hybrid_turboquant_make_cache` is reported as active TurboQuant and exposes
  the expected attention/companion layer split.

## Evidence

Passed:

```sh
PYTHONPATH=ExploitBotEngine /Applications/vMLX.app/Contents/Resources/bundled-python/python/bin/python3 -m unittest ExploitBotEngine.testsuite.test_runtime_status -v
PYTHONPATH=ExploitBotEngine python3 -m unittest ExploitBotEngine.testsuite.test_runtime_status -v
PYTHONPATH=ExploitBotEngine /Applications/vMLX.app/Contents/Resources/bundled-python/python/bin/python3 -m unittest discover -s ExploitBotEngine/testsuite -v
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
python3 -m compileall -q ExploitBotEngine
git diff --check
scripts/smoke-engine-api.sh
```

Bundled Python ran all 21 tests successfully. System Python ran 21 tests with
5 expected skips for optional FastAPI/Pydantic server dependencies. The smoke
API still reported `health.status=no_model`, effective cache and generation
metadata, cache memory diagnostics, and `models.count=0`.

## Remaining Proof Gap

This checkpoint proves API detection/reporting only. It does not prove that a
real MiniMax or Qwen model used TurboQuant cache encode/decode during
generation; that still requires a loaded-model cache hit/miss proof when memory
is available.
