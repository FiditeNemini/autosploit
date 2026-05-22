# Checkpoint 305 - Session Workflow Surface Proof Map

## Goal
Tie each named session workflow surface to concrete proof scripts.

## Changes
- Added `/qa/session-coverage.sessionWorkflowSurfaceProofs`.
- Added `sessionWorkflowSurfaceProofCount` and `sessionWorkflowSurfaceProofParity`.
- Mirrored session workflow proof count/parity into `/qa/coverage-index.groups.tabsAndSessions`.
- Extended the broad QA matrix smoke proof to check the new session workflow proof count/parity.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/session-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red session coverage proof failed because `/qa/session-coverage` listed
onboarding, sidebar lifecycle, overlays, model folder selection, persistence,
finding wizard submit, tab/phase navigation, and Activity Feed controls without
mapping each surface back to the proof scripts that exercise it. The green path
adds the proof map and mirrors the proof count/parity through the tabs/sessions
coverage-index group.
