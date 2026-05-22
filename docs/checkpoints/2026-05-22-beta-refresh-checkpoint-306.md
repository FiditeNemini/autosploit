# Checkpoint 306 - Tab Action Surface Proof Map

## Goal
Tie each per-tab action surface to concrete proof scripts.

## Changes
- Added `/qa/tab-action-coverage.tabActionSurfaceProofs`.
- Added `tabActionSurfaceProofCount` and `tabActionSurfaceProofParity`.
- Mirrored tab action proof count/parity into `/qa/coverage-index.groups.tabsAndSessions`.
- Extended the broad QA matrix smoke proof to check the new tab action proof count/parity.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/tab-action-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red tab action proof failed because `/qa/tab-action-coverage` listed Recon,
Web, Network, Creds, Exploit, Post, OSINT, Report, and Stash action surfaces
without mapping each surface back to the proof scripts that exercise its visible
buttons and action state. The green path adds that map and mirrors proof
count/parity through the tabs/sessions coverage-index group.
