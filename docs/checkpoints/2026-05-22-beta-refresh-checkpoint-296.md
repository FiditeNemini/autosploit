# Checkpoint 296 - Settings Surface Contract

## Goal
Make Settings coverage visible as stable operational surface metadata, not only
category rows and visual manifest counts.

## Changes
- Added `/qa/settings-coverage.settingsSurfaces`.
- Added `settingsSurfaceCount` and `settingsSurfaceParity`.
- Mirrored those fields into `/qa/coverage-index.groups.settingsAndVisuals`.
- Strengthened the focused Settings proof, coverage-index proof, and broad app
  QA matrix.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/settings-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red Settings proof failed because `/qa/settings-coverage` exposed category
metadata, routes, proof scripts, and manifests but not the operational surface
list for engine/model/runtime, context/cache, agents, CVEs, tools, inference
logs, and visual status proofs. The green path adds the surface list and checks
list/count/parity.
