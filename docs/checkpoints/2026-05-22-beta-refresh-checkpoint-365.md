# Checkpoint 365 - Tab Action Proof File Parity

## Goal

Make `/qa/tab-action-coverage` expose proof-file parity and mirror that flag
through `/qa/coverage-index.groups.tabsAndSessions`.

## Changes

- Added `proofFileParity` to `/qa/tab-action-coverage`.
- Added `tabActionProofFileParity` to the tabs/sessions coverage-index
  aggregate.
- Extended `scripts/tab-action-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/tab-action-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/tab-action-coverage` listed proof files for
per-tab actions without a route-owned machine-readable parity flag proving those
files exist. The green path makes tab-action proof-file existence auditable from
the route and mirrored by the top-level coverage index.
