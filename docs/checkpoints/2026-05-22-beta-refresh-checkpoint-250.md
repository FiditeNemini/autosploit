# Checkpoint 250 - Coverage Index Proof Category Counts

## Goal
Carry proof category counts into `/qa/coverage-index` so the top-level QA map
shows how proof coverage is distributed across agent, chat, context, runtime,
settings, tabs, tools, and visual surfaces.

## Changes
- Updated `scripts/coverage-index-proof.py` to compare
  `/qa/coverage-index.groups.appState.proofCategoryCounts` with
  `/qa/proof-ledger.categories`.
- Added `proofCategoryCounts` to `/qa/coverage-index.groups.appState`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red proof failed because `/qa/coverage-index.groups.appState` exposed the
total proof ledger count but not the category distribution. The green path lets
one aggregate QA response show whether proof coverage is concentrated in one
area or spread across the app, tool, parser, agent, runtime, and visual
surfaces.
