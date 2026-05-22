# Checkpoint 349 - Audit Proof Rollup Mirrors

## Goal

Make `/qa/coverage-index.groups.appState` preserve the audit ledger proof count
and source proof-ledger category rollup.

## Changes

- Added `auditProofCount` to the coverage-index app-state aggregate.
- Added audit source proof-ledger category counts, surfaces, surface count,
  total count, and parity to the coverage-index app-state aggregate.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/coverage-index.groups.appState` mirrored the
audit normalized proof-category rollup and source `other` count but not the
audit proof count or complete source proof-ledger category rollup. The green
path keeps audit proof accounting directly visible from the top-level QA index.
