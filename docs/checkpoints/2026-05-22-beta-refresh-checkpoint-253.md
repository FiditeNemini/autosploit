# Checkpoint 253 - Proof Category Parity Flag

## Goal
Make proof-category parity explicit in `/qa/coverage-index` and require the
broad app QA matrix to enforce it.

## Changes
- Updated `scripts/app-qa-matrix-smoke-proof.py` to require
  `/qa/coverage-index.groups.appState.proofCategoryParity == true`.
- Added `proofCategoryParity` to `/qa/coverage-index.groups.appState`.
- Updated `scripts/coverage-index-proof.py` to check the parity flag after
  validating category totals against `/qa/proof-ledger.proofCount`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The first broad-matrix total check passed immediately because the aggregate
already exposed `proofCategoryTotalCount`. The red proof was tightened to an
explicit missing parity flag. The green path now makes proof-category drift
visible as a boolean contract from the top-level coverage index and the broad
QA smoke gate.
