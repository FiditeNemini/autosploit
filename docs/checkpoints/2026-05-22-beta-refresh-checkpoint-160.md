# Checkpoint 160 - Tab Switch Actions

## Scope

- Route visible top-level tab switching through AppState and prove manual tab
  switches are auditable like the rest of the app controls.

## Changes

- Added `TabSwitchActionState` and exposed it as `/state.tabSwitchActions`.
- Added `AppState.switchToolTab(_:)` to switch tabs, pause follow-agent
  auto-tab tracking, and log the visible activity.
- Added `/qa/manual-tab-switch` for proof-driven tab switch testing.
- Updated `TabBarView` with an AppState-backed tab selection callback and wired
  it from `ContentView`.
- Added `scripts/tab-switch-action-proof.py`.
- Updated the system review and app flow inventory docs.

## Verification

- `python3 scripts/tab-switch-action-proof.py`
- `python3 scripts/visual-tab-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- `scripts/visual-tab-proof.py` refreshed the existing checkpoint-70 nested
  lifecycle screenshots while proving the tab surfaces still render.
