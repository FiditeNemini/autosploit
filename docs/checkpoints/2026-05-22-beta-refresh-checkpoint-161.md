# Checkpoint 161 - Phase Actions

## Scope

- Make the visible phase controls auditable through AppState.

## Changes

- Added `PhaseActionState` and exposed it as `/state.phaseActions`.
- `advancePhase()` and `setPhase(_:)` now record from/to phase, reset tool
  count, active phase guidance, and activity-feed status.
- Added `scripts/phase-action-proof.py`.
- Updated the app flow inventory and system review docs.

## Verification

- `python3 scripts/phase-action-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof drives the same `/phase` route used by visible AppState controls and
  verifies both Next Phase and direct phase selection behavior.
