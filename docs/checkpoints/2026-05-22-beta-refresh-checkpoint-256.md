# Checkpoint 256 - Coverage Index Audit Proof Surface

## Goal
Expose audit proof-surface breadth through `/qa/coverage-index.groups.appState` so the top-level QA index can prove `/qa/audit-ledger` carries the normalized proof-category surface count.

## Changes
- Updated `scripts/coverage-index-proof.py` to fetch `/qa/audit-ledger` and require `auditProofCategorySurfaceCount`.
- Added `auditProofCategorySurfaceCount` to the coverage-index app-state group.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red proof failed because the coverage-index app-state group exposed only `auditLedgerCount`. The green path keeps the aggregate size while also carrying the audit ledger's proof-category surface count for breadth-level QA accounting.
