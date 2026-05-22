# Checkpoint 313 - Settings Visual Proof Maps Aggregate

## Goal

Make the top-level coverage index preserve the exact proof maps for Settings
and visual UI surfaces.

## Changes

- Added `settingsSurfaceProofs` to `/qa/coverage-index.groups.settingsAndVisuals`.
- Added `visualSurfaceProofs` to `/qa/coverage-index.groups.settingsAndVisuals`.
- Extended `scripts/coverage-index-proof.py` to compare those maps against
  `/qa/settings-coverage` and `/qa/visual-coverage`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` to include the same aggregate
  proof-map checks.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the settings/visuals aggregate
exposed surface list/count/parity and proof count/parity, but not the
surface-to-proof maps themselves. The green path keeps each Settings and visual
surface traceable from the top-level QA index to the exact proof scripts that
validate it.
