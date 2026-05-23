# Beta Refresh Checkpoint 397

## Goal

Make agent-loop visual state-key parity visible from the agent-loop coverage route and mirrored by the top-level tabs/sessions coverage group.

## Changes

- Added `visualStateKeyParity` to `/qa/agent-loop-coverage`.
- Mirrored `agentLoopVisualStateKeyParity` through `/qa/coverage-index.groups.tabsAndSessions`.
- Strengthened agent-loop, coverage-index, and app QA matrix proofs so visual state keys must be a covered subset of the agent-loop state contract.
- Updated the system review and flow inventory documentation with the visual state-key parity contract.

## Proof

- `python3 scripts/agent-loop-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red agent-loop proof failed because the route exposed visual state keys and their count but not a parity flag. The green path makes active agent chat/results/feed visual routing auditable from the route and its aggregate mirror.
