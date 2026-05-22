# Checkpoint 271 - Coverage Index Proof Ledger Other Count

## Goal
Carry the source proof-ledger `other` category count into `/qa/coverage-index.groups.appState` so coverage-index consumers can audit uncategorized proof coverage without joining against `/qa/proof-ledger`.

## Changes
- Updated `scripts/coverage-index-proof.py` to require `proofLedgerCategoryOtherCount`.
- Added `proofLedgerCategoryOtherCount` to the app-state coverage-index group.
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
The red proof failed because the coverage index mirrored proof-ledger category counts, surfaces, total, and parity, but not the explicit source `other` count. The green path preserves that count directly in the app-state coverage group.
