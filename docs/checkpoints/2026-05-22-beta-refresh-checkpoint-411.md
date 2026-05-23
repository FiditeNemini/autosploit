# Beta Refresh Checkpoint 411

## Goal

Make the Exploit tab's search/prepare/execute staging, lifecycle state, copy
actions, raw output, and activity telemetry auditable from one QA route.

## Changes

- Added `/qa/exploit-coverage` for search/prepare/execute stages,
  listener/script/implant lifecycle state, copy paths for search/listener/
  script/implant, raw exploit output, and activity telemetry.
- Exposed Exploit surface, route, state-key, proof, and contract metadata with
  list/count/parity fields.
- Mirrored the Exploit coverage route through
  `/qa/coverage-index.groups.tabsAndSessions`.
- Added `scripts/exploit-coverage-proof.py` and strengthened coverage-index and
  broad app matrix proofs to keep Exploit stage/copy/lifecycle flow wired.
- Updated the system review and flow inventory docs with the route and mirror
  behavior.

## Proof

- `python3 scripts/exploit-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/exploit-coverage` did not exist. The green
path makes Exploit search/prepare/execute staging, lifecycle strips, copy paths,
raw output, and activity visibility measurable from both the source route and
the top-level tabs/session aggregate.
