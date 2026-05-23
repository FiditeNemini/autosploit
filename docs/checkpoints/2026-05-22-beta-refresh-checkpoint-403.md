# Beta Refresh Checkpoint 403

## Goal

Make agent-loop route, contract, action-telemetry, and state-key coverage expose
parity flags from the source route and the tabs/sessions aggregate.

## Changes

- Added `routeParity`, `contractParity`, `actionTelemetryFieldParity`, and
  `stateKeyParity` to `/qa/agent-loop-coverage`.
- Mirrored the same parity flags through
  `/qa/coverage-index.groups.tabsAndSessions`.
- Strengthened agent-loop, coverage-index, and broad app QA matrix proofs so
  full-auto/autopilot agent routes, contracts, telemetry fields, and state
  surfaces cannot silently drift from their lists/counts.
- Updated the system review and flow inventory with the agent-loop parity
  contract.

## Proof

- `python3 scripts/agent-loop-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red agent-loop proof failed because `/qa/agent-loop-coverage` exposed
route lists/counts but no route parity flag. The green path makes the agentic
loop route, contract, telemetry, and state-key surfaces measurable at both the
source route and top-level tabs/sessions coverage group.
