# Checkpoint 369 - Visual Proof File Parity

## Goal

Make `/qa/visual-coverage` expose proof-file parity and mirror that flag through
`/qa/coverage-index.groups.settingsAndVisuals`.

## Changes

- Added `proofFileParity` to `/qa/visual-coverage`.
- Added `visualProofFileParity` to the settings/visuals coverage-index
  aggregate.
- Extended `scripts/visual-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/visual-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/visual-coverage` listed visual proof scripts
and screenshot manifests without a route-owned machine-readable parity flag
proving those proof files exist. The green path keeps visual proof-file
existence auditable from the route and mirrored by the top-level coverage index.
