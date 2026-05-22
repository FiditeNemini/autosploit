# Checkpoint 266 - Proof Ledger Category Counts

## Goal
Expose the proof-ledger category count map directly from `/qa/proof-ledger` so tools can compare source ledger category accounting without walking nested category payloads.

## Changes
- Updated `scripts/proof-ledger-proof.py` to require `categoryCounts`.
- Added `categoryCounts` to `/qa/proof-ledger`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red proof failed because `/qa/proof-ledger` carried nested category payload counts, category total count, and parity, but not a direct category-count map. The green path makes the source ledger expose direct count accounting for every category bucket.
