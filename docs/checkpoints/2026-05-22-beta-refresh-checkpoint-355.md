# Checkpoint 355 - Agent Loop Proof List

## Goal

Make `/qa/coverage-index.groups.tabsAndSessions` preserve the concrete proof
files reported by `/qa/agent-loop-coverage`.

## Changes

- Added `agentLoopProofs` to the tabs/sessions coverage-index aggregate.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py` to compare the list against
  `/qa/agent-loop-coverage`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because the top-level tabs/sessions aggregate mirrored the
agent-loop proof count, phases, routes, contracts, modes, agent inheritance, and
telemetry fields, but did not preserve the actual agent-loop proof file list.
