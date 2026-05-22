# Checkpoint 260 - Coverage Index Audit Proof Surface Names

## Goal
Expose audit proof-surface names through `/qa/coverage-index.groups.appState` so the top-level QA index proves the audit ledger carries both named surface breadth and proof-category accounting.

## Changes
- Updated `scripts/coverage-index-proof.py` to require `auditProofCategorySurfaces`.
- Added `auditProofCategorySurfaces` to the coverage-index app-state group.
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
The red proof failed because the coverage-index app-state group carried the audit proof surface count, total, and parity but not the surface names. The green path makes the top-level index report the audit ledger's named proof surfaces directly.
