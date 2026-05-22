# Checkpoint 200 - Session Coverage Phase And Activity Routes

## Goal

Make `/qa/session-coverage` expose the phase and Activity Feed routes it already
claims through contracts and proofs.

## Changes

- Strengthened `scripts/session-coverage-proof.py` to require `/phase`,
  `/qa/seed-activity-actions`, `/qa/activity-action`, and `proofCount`.
- Updated `GET /qa/session-coverage` with those route entries and proof count.
- Updated docs with session aggregate route coverage.

## Proof

- `python3 scripts/session-coverage-proof.py`
- `python3 scripts/phase-action-proof.py`
- `python3 scripts/activity-feed-actions-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/session-coverage` listed `phaseActions` and
`activityFeedActions` but omitted the actual `/phase` and Activity Feed QA
routes.
