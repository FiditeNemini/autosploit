# Checkpoint 364 - Session Proof File Parity

## Goal

Make `/qa/session-coverage` expose proof-file parity and mirror that flag
through `/qa/coverage-index.groups.tabsAndSessions`.

## Changes

- Added `proofFileParity` to `/qa/session-coverage`.
- Added `sessionProofFileParity` to the tabs/sessions coverage-index aggregate.
- Extended `scripts/session-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/session-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/session-coverage` listed proof files without
a route-owned machine-readable parity flag proving those files exist. The green
path makes session workflow proof-file existence auditable from the route and
mirrored by the top-level coverage index.
