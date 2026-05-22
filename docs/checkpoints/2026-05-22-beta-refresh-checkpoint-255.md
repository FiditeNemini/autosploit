# Checkpoint 255 - Audit Proof Surface Count

## Goal
Carry the proof-category surface count into `/qa/audit-ledger` so the global audit rollup mirrors the coverage-index proof surface invariant.

## Changes
- Updated `scripts/audit-ledger-proof.py` to require `proofCategorySurfaceCount`.
- Added `proofCategorySurfaceCount` to `/qa/audit-ledger`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red proof failed because `/qa/audit-ledger` carried proof category counts, total, and parity, but not the normalized eight-surface count used by `/qa/coverage-index`. The green path lets the global audit endpoint report both the all-category accounting total and the core proof-surface breadth.
