# Checkpoint 273 - Coverage Index Audit Other Count

## Goal
Carry the audit ledger's source proof-ledger `other` count into `/qa/coverage-index` and lock it with the broad app QA matrix.

## Changes
- Updated `scripts/coverage-index-proof.py` to require `auditProofLedgerCategoryOtherCount`.
- Added `auditProofLedgerCategoryOtherCount` to `/qa/coverage-index.groups.appState`.
- Updated `scripts/app-qa-matrix-smoke-proof.py` to cross-check both source and audit `other` proof counts through `/qa/coverage-index`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red coverage-index proof failed because the app-state coverage group carried audit proof-category counts and parity but not the audit endpoint's source proof-ledger `other` count. The green path exposes that count and the broad smoke proof now checks both source and audit variants.
