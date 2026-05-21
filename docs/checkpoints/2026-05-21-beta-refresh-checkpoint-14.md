# Beta Refresh Checkpoint 14 — 2026-05-21

## Scope

Fourteenth checkpoint toward the beta-refresh objective:

- Stop Swift app defaults from masking model-folder generation defaults.
- Surface the broader effective generation config in Settings.
- Improve selectable text and minimum sizing in onboarding, settings, sheets,
  and modal-like panels.

## Changes

- Added `EngineConfig.useModelGenerationDefaults`, persisted as
  `engine.useModelGenerationDefaults`.
- `EngineManager` now omits `--temperature`, `--top-p`, and `--max-tokens`
  when model defaults are enabled, allowing `generation_config.json` and
  JANG generation fields from the selected model folder to drive startup
  defaults.
- `ChatService` now omits per-request `temperature` and `max_tokens` when
  model defaults are enabled, allowing server/model defaults to apply to chat
  completions.
- Multi-agent chat services inherit the same model-defaults policy.
- Settings adds a `Model Defaults` toggle and disables app-level temperature
  and max-token controls while model defaults are active.
- Swift `EngineEffectiveConfig` parses `top_k`, `min_p`,
  `repetition_penalty`, and stop-sequence metadata from `/health`.
- Runtime summary now displays the broader sampling state and adds a tooltip
  with the full value for truncated cells.
- Added text selection and minimum sizing to onboarding, Settings, the finding
  wizard, rename/deploy/stash sheets, and related modal surfaces.

## Visual Evidence

Captured the SwiftPM debug app after relaunch:

```text
/tmp/exploitbot-checkpoint14-front.png
```

Observed result:

- Onboarding remains dark and squared.
- Text selection is enabled at the onboarding root.
- Window remains at the content minimum and does not compress the navigation
  footer.

The current local app state opens onboarding first, so Settings visual proof is
source/build verified in this checkpoint; a later pass should exercise the
post-onboarding Settings panel directly.

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
