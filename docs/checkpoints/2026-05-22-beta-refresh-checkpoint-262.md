# Checkpoint 262 - Coverage Index Proof Surface Names

## Goal
Expose the coverage-index app-state proof surface names directly so `/qa/coverage-index.groups.appState` reports the same normalized proof surfaces it already counts.

## Changes
- Updated `scripts/coverage-index-proof.py` to require `proofCategorySurfaces`.
- Added `proofCategorySurfaces` to the coverage-index app-state group.
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
The red proof failed because the coverage-index app-state group exposed normalized proof category counts, count, total, and parity without naming the proof surfaces. The green path makes `agent`, `chat`, `context`, `runtime`, `settings`, `tabs`, `tools`, and `visual` machine-readable from the top-level index.
