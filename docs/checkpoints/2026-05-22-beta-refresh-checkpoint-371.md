# Checkpoint 371 - Subtab Proof File Parity

## Goal

Make `/qa/subtab-coverage` expose proof-file parity and mirror that flag through
both app-state and tabs/sessions coverage-index aggregates.

## Changes

- Added `proofFileParity` to `/qa/subtab-coverage`.
- Added `subtabStateProofFileParity` to
  `/qa/coverage-index.groups.appState`.
- Added `subtabProofFileParity` to
  `/qa/coverage-index.groups.tabsAndSessions`.
- Extended `scripts/subtab-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/subtab-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/subtab-coverage` listed per-tab subtab proof
files without a route-owned machine-readable parity flag proving those files
exist.
