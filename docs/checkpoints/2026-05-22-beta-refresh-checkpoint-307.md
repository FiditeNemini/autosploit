# Checkpoint 307 - Settings Surface Proof Map

## Goal
Tie each Settings coverage surface to concrete proof scripts.

## Changes
- Added `/qa/settings-coverage.settingsSurfaceProofs`.
- Added `settingsSurfaceProofCount` and `settingsSurfaceProofParity`.
- Mirrored settings surface proof count/parity into `/qa/coverage-index.groups.settingsAndVisuals`.
- Extended the broad QA matrix smoke proof to check the new Settings surface proof count/parity.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/settings-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red Settings proof failed because `/qa/settings-coverage` listed engine/
model/runtime, context/cache, agent, CVE, tool, inference-log, and visual status
surfaces without mapping each surface back to the scripts that prove it. The
green path adds that map and mirrors proof count/parity through the
settings/visuals coverage-index group.
