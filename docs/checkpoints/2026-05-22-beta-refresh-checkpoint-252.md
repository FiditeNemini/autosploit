# Checkpoint 252 - Coverage Index Proof Category Total

## Goal
Expose a proof-category total in `/qa/coverage-index` that proves category
accounting matches `/qa/proof-ledger.proofCount`.

## Changes
- Updated `scripts/coverage-index-proof.py` to require
  `/qa/coverage-index.groups.appState.proofCategoryTotalCount`.
- Added `proofCategoryTotalCount` to `/qa/coverage-index.groups.appState`.
- Kept `proofCategorySurfaceCount` as the eight core proof axes while summing
  all proof-ledger categories, including `other`, for total-count parity.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The first green attempt exposed that the proof ledger has an `other` category,
so summing only the eight core surfaces does not equal total proof count. The
final path keeps the core surface count at eight and computes the total from
all proof-ledger categories so `/qa/coverage-index` and `/qa/proof-ledger`
cannot drift silently.
