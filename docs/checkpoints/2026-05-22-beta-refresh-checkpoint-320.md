# Checkpoint 320 - Tab Activity Status Proof Map Aggregate

## Goal

Make the top-level coverage index preserve the tab activity status proof map
from `/qa/tool-flow-coverage` in the tabs/sessions group.

## Changes

- Added `tabActivityStatusProofs` to `/qa/coverage-index.groups.tabsAndSessions`.
- Extended `scripts/coverage-index-proof.py` to compare the aggregate status
  proof map against `/qa/tool-flow-coverage`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` to include the same aggregate
  tab activity status proof-map check.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the tabs/sessions aggregate exposed
tab activity status list/count/parity, the indicator contract, and proof
count/parity, but not the status-to-proof map itself. The green path keeps
running, done, failed, and canceled tab activity states traceable from the
top-level QA index to their proof scripts.
