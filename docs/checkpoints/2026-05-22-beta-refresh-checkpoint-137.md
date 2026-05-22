# Checkpoint 137 - Activity Feed Action State

## Scope

- Make Activity Feed copy and clear controls observable through AppState and QA
  proof routes.

## Changes

- Added `ActivityFeedActionState` and `/state.activityFeedActions`.
- Added deterministic QA routes:
  - `/qa/seed-activity-actions`
  - `/qa/activity-action`
- Routed Activity Feed header copy, row copy, row copy-with-timestamp,
  copy-visible, and clear controls through AppState while preserving clipboard
  behavior.
- Added `scripts/activity-feed-actions-proof.py`.

## Verification

- `python3 scripts/activity-feed-actions-proof.py`

## Notes

- The proof seeds tool, finding, and error activity rows, then verifies copied
  entry state, timestamped copy state, visible copy count, and clear state.
