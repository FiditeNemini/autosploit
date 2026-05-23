# Checkpoint 368 - Settings Proof File Parity

## Goal

Make `/qa/settings-coverage` expose proof-file parity and mirror that flag
through `/qa/coverage-index.groups.settingsAndVisuals`.

## Changes

- Added `proofFileParity` to `/qa/settings-coverage`.
- Added `settingsProofFileParity` to the settings/visuals coverage-index
  aggregate.
- Extended `scripts/settings-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/settings-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/settings-coverage` listed proof files for
settings categories, model/runtime/cache controls, agent controls, CVE settings,
tool inventory, inference logs, and visual settings states without a route-owned
machine-readable parity flag proving those files exist.
