# Checkpoint 295 - Tab Action Surface Contract

## Goal
Make per-tab direct action coverage visible as stable tab action surface
metadata.

## Changes
- Added `/qa/tab-action-coverage.tabActionSurfaces`.
- Added `tabActionSurfaceCount` and `tabActionSurfaceParity`.
- Mirrored those fields into `/qa/coverage-index.groups.tabsAndSessions`.
- Strengthened the focused tab-action proof, coverage-index proof, and broad app
  QA matrix.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/tab-action-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red tab-action proof failed because `/qa/tab-action-coverage` exposed routes,
contracts, proofs, and state keys but not the stable per-tab action surface list
for Recon, Web, Network, Creds, Exploit, Post, OSINT, Report, and Stash. The
green path adds the surface list and verifies list/count/parity.
