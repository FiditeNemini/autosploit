# Beta Refresh Checkpoint 436

## Goal

Add a visual surface matrix so every screenshot-backed UI surface has row-level
proof, manifest, view, and theme ownership.

## Changes

- Added `scripts/visual-surface-matrix-proof.py`.
- Added `/qa/visual-surface-matrix`.
- Added `/qa/visual-surface-matrix` to `/state.qaCoverage.stateRoutes`.
- Added one row per `/qa/visual-coverage.visualSurfaces` item with proof
  owners, manifest owners, `/qa/visual-coverage`, `/qa/view-inventory`, and
  `/qa/theme-inventory` linkage.
- Mirrored `visualSurfaceMatrixCount`,
  `visualSurfaceMatrixProofOwnerFileParity`,
  `visualSurfaceMatrixProofFileParity`, and
  `visualSurfaceMatrixManifestCount` into
  `/qa/coverage-index.groups.settingsAndVisuals`.
- Updated coverage-index and app matrix proofs to require the new visual
  surface matrix route and mirrors.
- Updated the system review and flow inventory docs with the visual surface
  matrix contract.

## Proof

- `python3 scripts/visual-surface-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/visual-surface-matrix` did not exist. The
green path keeps each visual surface tied to proof-owner files, manifest
ownership, view inventory, theme inventory, docs, and coverage-index mirrors.
