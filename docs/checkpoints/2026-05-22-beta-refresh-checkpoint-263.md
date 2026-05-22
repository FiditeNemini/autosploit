# Checkpoint 263 - Proof Ledger Category Surfaces

## Goal
Expose the normalized category surfaces directly from `/qa/proof-ledger` so the source proof ledger reports the same proof-surface set used by audit and coverage-index rollups.

## Changes
- Updated `scripts/proof-ledger-proof.py` to require `categorySurfaces`.
- Added `categorySurfaces` to `/qa/proof-ledger`.
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
The red proof failed because `/qa/proof-ledger` exposed category buckets and counts without a top-level normalized surface list. The green path makes `agent`, `chat`, `context`, `runtime`, `settings`, `tabs`, `tools`, and `visual` available from the source ledger itself.
