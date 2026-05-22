# Checkpoint 163 - Activity Feed Filters

## Scope

- Route Activity Feed filter changes through AppState and prove they are
  observable alongside copy and clear actions.

## Changes

- Added an `onFilter` callback to `ActivityFeedView` and wired it from
  `ContentView`.
- Added `recordActivityFeedFilter(_:)` and `filter:<name>` QA action handling
  in AppState.
- Extended `scripts/activity-feed-actions-proof.py` to cover Errors, Tools,
  and All filter changes plus filtered counts.
- Updated the app flow inventory and system review docs.

## Verification

- `python3 scripts/activity-feed-actions-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- Filter actions record the selected filter in `clipboardPreview` for the
  existing `/state.activityFeedActions` proof shape without introducing a
  separate state family.
