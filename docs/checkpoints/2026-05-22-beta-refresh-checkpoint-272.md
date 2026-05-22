# Checkpoint 272 - Audit Ledger Proof Ledger Other Count

## Goal
Carry the source proof-ledger `other` category count into `/qa/audit-ledger` so the audit endpoint preserves the same proof-category accounting exposed by `/qa/proof-ledger`.

## Changes
- Updated `scripts/audit-ledger-proof.py` to require `proofLedgerCategoryOtherCount`.
- Added `proofLedgerCategoryOtherCount` to `/qa/audit-ledger`.
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
The red proof failed because `/qa/audit-ledger` mirrored proof-ledger category counts, surfaces, total, and parity, but not the explicit `other` category count. The green path carries that source count directly.
