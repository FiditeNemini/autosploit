# Checkpoint 251 - QA Matrix Proof Surface Count

## Goal
Make the broad app QA matrix verify that the coverage index reports all core
proof-category surfaces, not just raw proof totals.

## Changes
- Updated `scripts/app-qa-matrix-smoke-proof.py` to require
  `/qa/coverage-index.groups.appState.proofCategorySurfaceCount == 8`.
- Added `proofCategorySurfaceCount` to `/qa/coverage-index.groups.appState`.
- Updated `scripts/coverage-index-proof.py` to cross-check the surface count
  against the `proofCategoryCounts` map.
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
The red proof failed because `/qa/coverage-index.groups.appState` exposed the
per-category proof counts but not a normalized surface-count guard. The green
path lets the broad matrix assert all eight core proof axes are represented:
agent, chat, context, runtime, settings, tabs, tools, and visual.
