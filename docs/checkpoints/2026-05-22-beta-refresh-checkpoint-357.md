# Checkpoint 357 - Agent Loop Mode Count

## Goal

Make `/qa/agent-loop-coverage` own the interaction-mode count and mirror that
count through `/qa/coverage-index.groups.tabsAndSessions`.

## Changes

- Added `modeCount` to `/qa/agent-loop-coverage`.
- Added `agentLoopModeCount` to the tabs/sessions coverage-index aggregate.
- Extended `scripts/agent-loop-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/agent-loop-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/agent-loop-coverage` exposed the mode behavior
map for autopilot, copilot, and manual, but did not expose a machine-readable
mode count owned by that route.
