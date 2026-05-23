# Checkpoint 376 - Session Workflow Proof File Parity

## Goal

Make `/qa/session-coverage` expose file parity for session workflow surface
proof maps and mirror that flag through the tabs/sessions coverage-index
aggregate.

## Changes

- Added `sessionWorkflowSurfaceProofFileParity` to `/qa/session-coverage`.
- Mirrored `sessionWorkflowSurfaceProofFileParity` through
  `/qa/coverage-index.groups.tabsAndSessions`.
- Extended `scripts/session-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/session-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/session-coverage` listed session workflow
surface proof files without an explicit route-owned file-parity flag for the
mapped proof files.
