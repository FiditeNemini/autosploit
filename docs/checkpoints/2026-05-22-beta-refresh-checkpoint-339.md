# Checkpoint 339 - Tab Session Aggregate Detail

## Goal

Make `/qa/coverage-index.groups.tabsAndSessions` preserve the detailed session
and per-tab action wiring already exposed by `/qa/session-coverage` and
`/qa/tab-action-coverage`.

## Changes

- Added session route list/count, contract map/count, proof list/count, and
  state-key list/count to the tabs/sessions aggregate.
- Added tab action tab list, route list/count, contract map/count, proof
  list/count, and action-state-key list/count.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because the aggregate carried session and tab action
surface proof maps, but not the route, contract, proof-list, tab-list, or
state-key detail from the underlying endpoints. The green path makes individual
tab/action and session flow wiring auditable from the top-level QA index.
