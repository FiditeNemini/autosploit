# Checkpoint 267 - Coverage Index Source Proof Category Counts

## Goal
Expose the source proof-ledger category count map through `/qa/coverage-index.groups.appState` so the top-level QA index can compare `/qa/proof-ledger.categoryCounts` directly.

## Changes
- Updated `scripts/coverage-index-proof.py` to require `proofLedgerCategoryCounts`.
- Added `proofLedgerCategoryCounts` to the coverage-index app-state group.
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
The red proof failed because the coverage-index app-state group carried locally normalized proof category counts but not the direct `/qa/proof-ledger.categoryCounts` map. The green path makes the top-level index expose source-ledger category accounting directly.
