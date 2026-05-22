# Checkpoint 268 - Coverage Index Source Proof Category Accounting

## Goal
Expose the source proof-ledger category surfaces, surface count, total count, and parity through `/qa/coverage-index.groups.appState` so the top-level QA index carries the full `/qa/proof-ledger` accounting contract.

## Changes
- Updated `scripts/coverage-index-proof.py` to require source proof-ledger category surfaces, surface count, total count, and parity.
- Added `proofLedgerCategorySurfaces`, `proofLedgerCategorySurfaceCount`, `proofLedgerCategoryTotalCount`, and `proofLedgerCategoryParity` to the coverage-index app-state group.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red proof failed because the coverage-index app-state group carried `/qa/proof-ledger.categoryCounts` but not the source ledger's surface names, surface count, total count, or parity. The green path makes the top-level index carry the complete source proof-ledger category accounting rollup.
