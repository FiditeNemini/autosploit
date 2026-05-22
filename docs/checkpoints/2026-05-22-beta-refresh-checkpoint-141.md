# Checkpoint 141 - Sidebar Operation Actions

## Scope

- Make Sidebar operation create, switch, rename, and delete actions observable
  through AppState instead of only mutating operation state directly.

## Changes

- Added `SidebarActionState` and exposed it as `/state.sidebarActions`.
- Added deterministic QA routes `/qa/seed-sidebar-actions` and
  `/qa/sidebar-action`.
- Routed Sidebar plus button, row tap, rename sheet, and delete confirmation
  through AppState sidebar action wrappers.
- Added `scripts/sidebar-actions-proof.py`.

## Verification

- `python3 scripts/sidebar-actions-proof.py`
- `python3 scripts/mode-selection-flow-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies operation count, active operation transitions, last action,
  operation id/name telemetry, and activity-feed visibility for each Sidebar
  action.
