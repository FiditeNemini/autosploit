# Beta Refresh Checkpoint 416

## Goal

Make agent tool-call authorization auditable as its own live contract instead
of relying on scattered manual/copilot/autopilot behavior notes.

## Changes

- Added `scripts/agent-tool-authorization-proof.py`.
- Added `/qa/agent-tool-authorization-coverage` with mode policies, approve/
  reject routes, pending approval state, state keys, visual surfaces,
  transitions, and proof-file parity.
- Mirrored the authorization contract into
  `/qa/coverage-index.groups.tabsAndSessions`.
- Added the new route to `/state.qaCoverage.stateRoutes`.
- Updated the app matrix and coverage-index proofs to require the authorization
  endpoint and its index mirror.
- Updated the system review and flow inventory docs with the explicit
  authorization contract.

## Proof

- `python3 scripts/agent-tool-authorization-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because the app had behavioral tests for manual,
copilot, and autopilot tool handling, but no route-owned authorization
contract. The green path now proves the pending approval snapshot and the
approve/reject clearing behavior against the live app API.
