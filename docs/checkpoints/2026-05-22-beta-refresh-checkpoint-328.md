# Checkpoint 328 - Audit Rollup Count Aggregate

## Goal

Make the top-level coverage index preserve audit artifact, checkpoint, and gap
rollup counts from `/qa/audit-ledger`.

## Changes

- Added audit artifact counts to `/qa/coverage-index.groups.appState`:
  `auditVisualManifestCount`, `auditVisualCaptureCount`,
  `auditMissingVisualCaptureCount`, and `auditLiveProofCount`.
- Added audit checkpoint and gap counts:
  `auditCheckpointCount`, `auditCompleteCheckpointCount`,
  `auditIncompleteCheckpointCount`, and `auditCurrentGapCount`.
- Extended `scripts/coverage-index-proof.py` to compare those aggregate fields
  against `/qa/audit-ledger`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` with the same broad smoke
  checks.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the app-state aggregate exposed the
audit total, proof-category rollups, and live proof failure details, but not the
audit artifact, checkpoint, and current-gap source-domain counts. The green
path keeps audit totals explainable from the top-level QA index.
