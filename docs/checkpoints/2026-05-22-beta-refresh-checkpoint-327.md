# Checkpoint 327 - Audit Live Proof Status Aggregate

## Goal

Make the top-level coverage index preserve audit live-proof ok/failure status
from `/qa/audit-ledger`.

## Changes

- Added `auditLiveProofOkCount`, `auditFailedLiveProofCount`, and
  `auditFailedLiveProofs` to `/qa/coverage-index.groups.appState`.
- Extended `scripts/coverage-index-proof.py` to compare those aggregate fields
  against `/qa/audit-ledger`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` with the same broad smoke
  checks.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the app-state aggregate exposed the
audit ledger total and proof category rollups, but not the live-proof ok count,
failed live-proof count, or failed live-proof paths. The green path keeps live
JSON evidence failures visible from the top-level QA index.
