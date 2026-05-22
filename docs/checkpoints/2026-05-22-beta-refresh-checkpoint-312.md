# Checkpoint 312 - Agent Loop Phase Proof Map Aggregate

## Goal

Make the top-level coverage index identify which proof scripts validate each
agentic loop phase.

## Changes

- Added `agentLoopPhaseProofs` to `/qa/coverage-index.groups.tabsAndSessions`.
- Extended `scripts/coverage-index-proof.py` to compare that map against
  `/qa/agent-loop-coverage.loopPhaseProofs`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` to include the same
  aggregate phase-proof map/count/parity check.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the tabs/sessions aggregate exposed
agent-loop phase list/count/parity and proof count/parity, but not the
phase-to-proof map itself. The green path now keeps each agentic loop phase
traceable from the top-level QA index to the exact proof scripts that validate
it.
