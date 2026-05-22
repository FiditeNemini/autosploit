# Checkpoint 347 - Artifact Source Count Mirrors

## Goal

Make `/qa/coverage-index.groups.appState` preserve source artifact ledger
visual-capture and live-proof success counts.

## Changes

- Added `artifactLedgerVisualCaptureCount` to the coverage-index app-state
  aggregate.
- Added `artifactLedgerLiveProofOkCount` to the coverage-index app-state
  aggregate.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/coverage-index.groups.appState` mirrored
artifact evidence paths and status maps but not the source artifact
`visualCaptureCount` or `liveProofOkCount`. The green path keeps source artifact
totals directly auditable from the top-level QA index.
