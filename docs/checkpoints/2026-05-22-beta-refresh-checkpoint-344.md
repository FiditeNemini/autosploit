# Checkpoint 344 - Proof Ledger Category Aggregate

## Goal

Make `/qa/coverage-index.groups.appState` preserve the detailed proof-ledger
category map from `/qa/proof-ledger`.

## Changes

- Added `proofLedgerCategories` to the app-state aggregate.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because the app-state aggregate preserved proof-ledger
category counts/surfaces/other/total/parity but not the detailed category map.
The green path keeps categorized proof ownership visible from the top-level QA
index.
