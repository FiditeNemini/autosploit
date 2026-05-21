# Beta Refresh Checkpoint 15 — 2026-05-21

## Scope

Fifteenth checkpoint toward the beta-refresh objective:

- Complete app-level `top_p` override wiring when model-folder generation
  defaults are disabled.
- Keep model-folder defaults as the default behavior.

## Changes

- Added `ChatService.topP`.
- When `useModelGenerationDefaults` is disabled, chat requests now send
  `top_p` alongside `temperature` and `max_tokens`.
- Multi-agent chat services now inherit `topP` from `EngineConfig`.
- Settings now exposes a `Top P` slider, disabled while model defaults are
  enabled.
- Existing persisted `engine.topP` is now visible and applied through the full
  Swift request path.

## Evidence

Passed:

```sh
swift build
python3 -m compileall -q ExploitBotEngine
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
PYTHONPATH=ExploitBotEngine /Applications/vMLX.app/Contents/Resources/bundled-python/python/bin/python3 -m unittest discover -s ExploitBotEngine/testsuite -v
scripts/smoke-engine-api.sh
git diff --check
```

System Python ran 17 tests with 3 expected skips for optional runtime packages.
Bundled Python ran all 17 tests successfully.
