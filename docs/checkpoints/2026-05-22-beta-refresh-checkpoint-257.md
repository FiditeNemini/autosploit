# Checkpoint 257 - Coverage Index Audit Proof Parity

## Goal
Expose audit proof-category parity through `/qa/coverage-index.groups.appState` so the top-level QA index can prove `/qa/audit-ledger` carries both proof-surface breadth and all-category accounting parity.

## Changes
- Updated `scripts/coverage-index-proof.py` to require `auditProofCategoryParity`.
- Added `auditProofCategoryParity` to the coverage-index app-state group.
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
The red proof failed because the coverage-index app-state group carried the audit proof surface count but not the audit ledger's proof-category parity flag. The green path makes the top-level index prove both audit breadth and audit accounting consistency.
