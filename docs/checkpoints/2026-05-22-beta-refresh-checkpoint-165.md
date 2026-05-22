# Checkpoint 165 - Activity Feed Verbosity

## Scope

- Route Activity Feed verbosity changes through AppState and prove the filtered
  visible entry count follows the selected verbosity.

## Changes

- Added `onVerbosity` callback support to `ActivityFeedView`.
- Wired Activity Feed verbosity selection from `ContentView` to AppState.
- Added `recordActivityFeedVerbosity(_:)` and `verbosity:<name>` QA handling.
- Extended `scripts/activity-feed-actions-proof.py` to cover Minimal and Debug
  verbosity counts.
- Updated app flow inventory and system review docs.

## Verification

- `python3 scripts/activity-feed-actions-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- Minimal hides tool-start and info rows, while Debug includes the full activity
  stream; the proof asserts both counts before copy-visible runs.
