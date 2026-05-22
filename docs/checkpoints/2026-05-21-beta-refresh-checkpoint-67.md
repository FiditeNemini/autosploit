# Checkpoint 67 - App-Only Settings Apply

## Changes

- Split Settings footer actions into `Apply App Settings` and
  `Apply & Restart Engine`.
- Added `AppState.applyAppSettings(...)` for chat loop, context catalogue, and
  agent settings that do not need an engine restart.
- Added QA state fields for chat max iterations, context source toggles, and
  agent settings.
- Added `scripts/settings-apply-proof.py` to verify app-only settings update
  without changing engine connection state.

## Verified

- `python3 scripts/settings-apply-proof.py`
- `python3 scripts/context-catalog-proof.py`
- `python3 scripts/live-turn-harness.py`
- `swift build --package-path ExploitBot`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`

## Notes

- App-launching proof scripts should be run serially because they intentionally
  terminate existing `ExploitBot` processes before launching the QA app.
