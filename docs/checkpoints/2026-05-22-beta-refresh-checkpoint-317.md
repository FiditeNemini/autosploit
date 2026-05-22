# Checkpoint 317 - Subtab Map Aggregate

## Goal

Make the top-level coverage index preserve the per-tab subtab navigation
contract from `/qa/subtab-coverage`.

## Changes

- Changed `/qa/coverage-index` to build from the live `AppState` so it can
  mirror active subtab state.
- Added `subtabTabs` to `/qa/coverage-index.groups.tabsAndSessions`.
- Added `subtabProofCount` to `/qa/coverage-index.groups.tabsAndSessions`.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py` to compare the aggregate subtab map
  against `/qa/subtab-coverage`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the tabs/sessions aggregate exposed
covered tab count but not the per-tab default, active, valid subtab list, and
proof-file mapping from `/qa/subtab-coverage`. The green path keeps that
navigation contract visible from the top-level QA index.
