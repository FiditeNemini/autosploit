# Beta Refresh Checkpoint 412

## Goal

Make the Post tab's lifecycle state, attribution rows, copy actions, raw
post-exploitation output, and activity telemetry auditable from one QA route.

## Changes

- Added `/qa/post-coverage` for PrivEsc/AD/lateral lifecycle state,
  attribution rows, copy paths for PrivEsc/AD/lateral/attribution, raw output,
  and activity telemetry.
- Exposed Post surface, route, state-key, proof, and contract metadata with
  list/count/parity fields.
- Mirrored the Post coverage route through
  `/qa/coverage-index.groups.tabsAndSessions`.
- Added `scripts/post-coverage-proof.py` and strengthened coverage-index and
  broad app matrix proofs to keep Post attribution/copy/lifecycle flow wired.
- Updated the system review and flow inventory docs with the route and mirror
  behavior.

## Proof

- `python3 scripts/post-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/post-coverage` did not exist. The green path
makes Post attribution rows, lifecycle strips, copy paths, raw output, and
activity visibility measurable from both the source route and the top-level
tabs/session aggregate.
