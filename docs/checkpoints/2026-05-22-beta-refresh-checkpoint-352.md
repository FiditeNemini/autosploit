# Checkpoint 352 - Audit Gap Contract Count

## Goal

Make `/qa/coverage-index.groups.appState` preserve the audit ledger gap
contract count alongside the source gap contract count.

## Changes

- Added `auditGapContractCount` to the coverage-index app-state aggregate.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because the aggregate mirrored `/qa/audit-ledger.gapContracts`
but did not expose a machine-readable audit gap contract count. The green path
keeps source and audit gap-contract accounting visible from the top-level QA index.
