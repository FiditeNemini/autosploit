# Checkpoint 333 - Agent Loop Runtime Count Aggregate

## Goal

Make `/qa/coverage-index.groups.tabsAndSessions` preserve the agent-loop
runtime and count fields that prove the current full-auto loop guard and visible
state wiring.

## Changes

- Added `agentLoopCurrentMode`, `agentLoopMaxIterations`, and
  `agentLoopProofCount`.
- Added `agentLoopVisualStateKeyCount`.
- Added `agentLoopRouteCount` and `agentLoopContractCount`.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red coverage-index proof failed because the tabs/sessions aggregate mirrored
agent-loop mode/contract maps but not the live current mode, max-iteration
guard, proof count, visual-state-key count, route count, or contract count. The
green path keeps the full-auto loop guard and visible agent status surface
auditable from the top-level QA index.
