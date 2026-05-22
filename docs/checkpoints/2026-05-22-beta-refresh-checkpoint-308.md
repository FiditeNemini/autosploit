# Checkpoint 308 - Visual Surface Proof Map

## Goal
Tie each screenshot-backed visual coverage surface to concrete visual proof scripts.

## Changes
- Added `/qa/visual-coverage.visualSurfaceProofs`.
- Added `visualSurfaceProofCount` and `visualSurfaceProofParity`.
- Mirrored visual surface proof count/parity into `/qa/coverage-index.groups.settingsAndVisuals`.
- Extended the broad QA matrix smoke proof to check the new visual surface proof count/parity.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/visual-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red visual coverage proof failed because `/qa/visual-coverage` listed chat,
Settings/cache, context/audit, tab/subtab, OSINT, report/stash,
unsupported/post, tool-action, and CVE/tool-settings visual surfaces without
mapping each surface to the scripts that prove it with screenshots and manifest
artifacts. The green path adds that map and mirrors proof count/parity through
the settings/visuals coverage-index group.
