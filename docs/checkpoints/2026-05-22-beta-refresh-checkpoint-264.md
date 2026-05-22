# Checkpoint 264 - Proof Ledger Category Surface Count

## Goal
Expose the normalized category surface count directly from `/qa/proof-ledger` so the source proof ledger carries both the surface names and their count.

## Changes
- Updated `scripts/proof-ledger-proof.py` to require `categorySurfaceCount`.
- Added `categorySurfaceCount` to `/qa/proof-ledger`.
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
The red proof failed because `/qa/proof-ledger` exposed the normalized category surfaces without their direct count. The green path gives the source ledger the same surface-count invariant carried by audit and coverage rollups.
