# Checkpoint 377 - Tab Action Surface Proof File Parity

## Goal

Make `/qa/tab-action-coverage` expose file parity for tab action surface proof
maps and mirror that flag through the tabs/sessions coverage-index aggregate.

## Changes

- Added `tabActionSurfaceProofFileParity` to `/qa/tab-action-coverage`.
- Mirrored `tabActionSurfaceProofFileParity` through
  `/qa/coverage-index.groups.tabsAndSessions`.
- Extended `scripts/tab-action-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/tab-action-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/tab-action-coverage` listed tab action
surface proof files without an explicit route-owned file-parity flag for the
mapped proof files.
