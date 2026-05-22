# Checkpoint 258 - Coverage Index Audit Proof Total

## Goal
Expose audit proof-category total count through `/qa/coverage-index.groups.appState` so the top-level QA index proves `/qa/audit-ledger` carries the same all-category proof accounting total it validates with parity.

## Changes
- Updated `scripts/coverage-index-proof.py` to require `auditProofCategoryTotalCount`.
- Added `auditProofCategoryTotalCount` to the coverage-index app-state group.
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
The red proof failed because the coverage-index app-state group carried the audit proof surface count and parity but not the audit proof-category total. The green path makes the top-level index prove audit breadth, total accounting, and parity together.
