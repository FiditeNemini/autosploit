# Checkpoint 345 - Artifact Failed Live Proof Aggregate

## Goal

Make `/qa/artifact-ledger` and `/qa/coverage-index.groups.appState` expose the
source failed-live-proof count and list together.

## Changes

- Added `failedLiveProofCount` to `/qa/artifact-ledger`.
- Added `artifactLedgerFailedLiveProofCount` and
  `artifactLedgerFailedLiveProofs` to the coverage-index app-state aggregate.
- Extended `scripts/artifact-ledger-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/artifact-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red source proof failed because `/qa/artifact-ledger` exposed
`failedLiveProofs` without a matching `failedLiveProofCount`. The green path
keeps failed live JSON evidence visible from both the source artifact ledger and
the top-level QA index.
