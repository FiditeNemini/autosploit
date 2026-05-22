# Checkpoint 294 - Session Workflow Surface Contract

## Goal
Make cross-app session workflow coverage explicit from aggregate QA routes.

## Changes
- Added `/qa/session-coverage.sessionWorkflowSurfaces`.
- Added `sessionWorkflowSurfaceCount` and `sessionWorkflowSurfaceParity`.
- Mirrored those fields into `/qa/coverage-index.groups.tabsAndSessions`.
- Strengthened the focused session proof, coverage-index proof, and broad app
  QA matrix.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/session-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red session coverage proof failed because `/qa/session-coverage` exposed
routes, actions, and state keys but not the stable workflow surface list behind
onboarding, Sidebar lifecycle, overlays, model folder selection, persistence,
finding wizard submit, tab/phase navigation, and Activity Feed controls. The
green path names those surfaces and verifies list/count/parity.
