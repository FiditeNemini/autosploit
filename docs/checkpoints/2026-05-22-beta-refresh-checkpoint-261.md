# Checkpoint 261 - Coverage Index Audit Proof Category Counts

## Goal
Expose audit proof-category counts through `/qa/coverage-index.groups.appState` so the top-level QA index can compare the audit ledger's full proof-category accounting map.

## Changes
- Updated `scripts/coverage-index-proof.py` to require `auditProofCategoryCounts`.
- Added `auditProofCategoryCounts` to the coverage-index app-state group.
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
The red proof failed because the coverage-index app-state group carried the audit proof surfaces, count, total, and parity but not the audit proof-category count map. The green path makes the top-level index expose the full audit category accounting contract.
