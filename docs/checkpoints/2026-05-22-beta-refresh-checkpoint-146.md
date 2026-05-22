# Checkpoint 146 - Tool Settings Actions

## Scope

- Make Settings > Tools Refresh, Install, and Install All Missing controls route
  through AppState and expose action telemetry.

## Changes

- Added `ToolSettingsActionState` and exposed it as
  `/state.toolSettingsActions`.
- Added deterministic QA route `/qa/tool-settings-action`.
- Routed `ToolSettingsView` buttons through AppState callbacks supplied by
  `SettingsView`.
- Added testing-mode deterministic install behavior for tool settings proofs;
  production mode still calls the real `ToolInstaller`.
- Added `scripts/tool-settings-actions-proof.py`.

## Verification

- `python3 scripts/tool-settings-actions-proof.py`
- `python3 scripts/tool-settings-status-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies action name, target tool, installed/missing counts,
  install log changes, state exposure, and visible activity-feed entries.
