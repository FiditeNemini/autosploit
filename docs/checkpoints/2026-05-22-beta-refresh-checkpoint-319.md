# Checkpoint 319 - Tab Action Proof Map Aggregate

## Goal

Make the top-level coverage index preserve the tab-action surface proof map from
`/qa/tab-action-coverage`.

## Changes

- Added `tabActionSurfaceProofs` to
  `/qa/coverage-index.groups.tabsAndSessions`.
- Extended `scripts/coverage-index-proof.py` to compare the aggregate tab
  action proof map against `/qa/tab-action-coverage`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` to include the same aggregate
  tab action proof-map check.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the tabs/sessions aggregate exposed
tab action surfaces plus proof count/parity, but not the surface-to-proof map
itself. The green path keeps recon, web, network, creds, exploit, post, OSINT,
report, and stash action surfaces traceable from the top-level QA index to their
proof scripts.
