# Checkpoint 329 - Audit List and Gap Detail Aggregate

## Goal

Make the top-level coverage index preserve audit list and gap detail fields
from `/qa/audit-ledger`.

## Changes

- Added `auditMissingVisualCaptures` to `/qa/coverage-index.groups.appState`.
- Added `auditCompleteCheckpoints` and `auditIncompleteCheckpoints`.
- Added `auditNextGap`, `auditOpenGapIds`, and `auditGapContracts`.
- Extended `scripts/coverage-index-proof.py` to compare those aggregate fields
  against `/qa/audit-ledger`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` with the same broad smoke
  checks.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the app-state aggregate exposed
audit rollup counts but not audit list fields for missing captures,
complete/incomplete checkpoints, or the current gap contract. The green path
keeps audit detail traceable from the top-level QA index without reducing it to
counts.
