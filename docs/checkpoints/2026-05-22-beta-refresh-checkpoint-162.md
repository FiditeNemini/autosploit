# Checkpoint 162 - Settings Engine Actions

## Scope

- Make Settings engine controls auditable through AppState, starting with the
  visible Stop Engine path.

## Changes

- Added `SettingsEngineActionState` and exposed it as
  `/state.settingsEngineActions`.
- `startEngine()` and `stopEngine()` now record previous/current running state,
  model label, health status, summary, and activity-feed visibility.
- Added `scripts/settings-engine-actions-proof.py`.
- Updated the app flow inventory and system review docs.

## Verification

- `python3 scripts/settings-engine-actions-proof.py`
- `python3 scripts/settings-apply-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof uses `/engine/mock` to avoid loading a real model while still
  proving that the Settings stop action transitions the engine state and exposes
  the same model label the user saw as running.
