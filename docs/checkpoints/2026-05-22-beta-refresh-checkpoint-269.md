# Checkpoint 269 - Audit Source Proof Category Accounting

## Goal
Expose source proof-ledger category accounting through `/qa/audit-ledger` so the global audit rollup carries the full `/qa/proof-ledger` category contract.

## Changes
- Updated `scripts/audit-ledger-proof.py` to require source proof-ledger category counts, surfaces, surface count, total count, and parity.
- Added `proofLedgerCategoryCounts`, `proofLedgerCategorySurfaces`, `proofLedgerCategorySurfaceCount`, `proofLedgerCategoryTotalCount`, and `proofLedgerCategoryParity` to `/qa/audit-ledger`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red proof failed because `/qa/audit-ledger` carried its own proof category rollup but not the source `/qa/proof-ledger` category accounting fields. The green path makes the global audit ledger expose the source proof-ledger category contract directly.
