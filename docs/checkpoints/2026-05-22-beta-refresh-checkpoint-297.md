# Checkpoint 297 - Visual Surface Contract

## Goal
Make screenshot-backed visual proof coverage visible as stable surface metadata.

## Changes
- Added `/qa/visual-coverage.visualSurfaces`.
- Added `visualSurfaceCount` and `visualSurfaceParity`.
- Mirrored those fields into `/qa/coverage-index.groups.settingsAndVisuals`.
- Strengthened the focused visual proof, coverage-index proof, and broad app QA
  matrix.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/visual-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red visual proof failed because `/qa/visual-coverage` exposed manifests,
routes, contracts, and capture counts but not the stable visual surface list for
chat/scroll, settings/cache, context/audit, tabs/subtabs, OSINT screenshots,
report/stash, unsupported/post states, tool panels, and CVE/tool settings. The
green path adds that surface list and checks list/count/parity.
