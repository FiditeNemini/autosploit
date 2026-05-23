# Beta Refresh Checkpoint 409

## Goal

Make the Network tab's protocol scan, copy actions, parsed hosts, lifecycle
state, and activity telemetry auditable from one QA route.

## Changes

- Added `/qa/network-coverage` for parsed network hosts, Protocol Scan, copy
  paths for protocols/SNMP/captures/MITM/tunnels, capture/MITM/tunnel lifecycle
  state, and activity telemetry.
- Exposed Network surface, route, state-key, proof, and contract metadata with
  list/count/parity fields.
- Mirrored the Network coverage route through
  `/qa/coverage-index.groups.tabsAndSessions`.
- Added `scripts/network-coverage-proof.py` and strengthened coverage-index and
  broad app matrix proofs to keep Network scan/copy/lifecycle flow wired.
- Updated the system review and flow inventory docs with the route and mirror
  behavior.

## Proof

- `python3 scripts/network-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/network-coverage` did not exist. The green
path makes Network protocol actions, copy paths, lifecycle strips, parsed hosts,
and activity visibility measurable from both the source route and the top-level
tabs/session aggregate.
