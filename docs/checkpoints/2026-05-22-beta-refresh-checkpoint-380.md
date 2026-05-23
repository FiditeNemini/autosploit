# Checkpoint 380 - Settings Visual Surface Proof File Parity

## Goal

Make `/qa/settings-coverage` and `/qa/visual-coverage` expose file parity for
their surface proof maps, then mirror both flags through the settings/visuals
coverage-index aggregate.

## Changes

- Added `settingsSurfaceProofFileParity` to `/qa/settings-coverage`.
- Added `visualSurfaceProofFileParity` to `/qa/visual-coverage`.
- Mirrored both fields through `/qa/coverage-index.groups.settingsAndVisuals`.
- Extended `scripts/settings-coverage-proof.py`,
  `scripts/visual-coverage-proof.py`, `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/settings-coverage-proof.py`
- `python3 scripts/visual-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/settings-coverage` listed surface proof files
without an explicit route-owned file-parity flag for the mapped proof files.
