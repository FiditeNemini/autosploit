# Beta Refresh Checkpoint 41

Date: 2026-05-21

## Scope

- Added launch-time provenance for parser and generation defaults.
- Tagged parser defaults as `jang_capabilities`, `jang_config`, `model_registry`, `cli`, or `unset`.
- Tagged generation defaults as `jang_generation`, `generation_config`, `cli`, `launcher_default`, or `unset`.
- Exposed provenance through `effective_config.sources` on `/health` and `/v1/models`.
- Parsed and displayed selectable `Sampling Source` and `Parser Source` rows in Settings.

## Files

- `ExploitBotEngine/launch.py`
- `ExploitBotEngine/vmlx_engine/server.py`
- `ExploitBotEngine/vmlx_engine/runtime_status.py`
- `ExploitBotEngine/testsuite/test_launch_model_defaults.py`
- `ExploitBotEngine/testsuite/test_runtime_status.py`
- `ExploitBot/Sources/ExploitBot/Services/EngineManager.swift`
- `ExploitBot/Sources/ExploitBot/Views/Settings/SettingsView.swift`

## Verification

- `swift build --package-path ExploitBot`
- `PYTHONPATH=. uv run --extra dev pytest -q`

## Result

- Swift app: build passed.
- Engine: `24 passed, 3 warnings`.

## Notes

- This makes model-folder generation defaults auditable through the API and app instead of only inferred from launch arguments.
- This is provenance/metadata proof; it is not a live model generation proof.
