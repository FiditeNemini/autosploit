# Checkpoint 270 - Proof Ledger Other Category Count

## Goal
Expose the proof-ledger `other` category count directly from `/qa/proof-ledger` so uncategorized proof coverage can be tracked without walking nested category payloads.

## Changes
- Updated `scripts/proof-ledger-proof.py` to require `categoryOtherCount`.
- Added `categoryOtherCount` to `/qa/proof-ledger`.
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
The red proof failed because `/qa/proof-ledger` exposed the `other` bucket only through nested category payloads and `categoryCounts`. The green path makes the uncategorized proof bucket directly machine-readable.
