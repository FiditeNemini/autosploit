# Checkpoint 358 - Agent Loop Contract Count

## Goal

Make `/qa/agent-loop-coverage` own the agent-loop contract count and mirror that
count through `/qa/coverage-index.groups.tabsAndSessions`.

## Changes

- Added `contractCount` to `/qa/agent-loop-coverage`.
- Updated `agentLoopContractCount` in the tabs/sessions coverage-index aggregate
  to consume the route-owned count.
- Extended `scripts/agent-loop-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/agent-loop-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/agent-loop-coverage` exposed the full contract
map for manual, copilot, autopilot, deployed-agent inheritance, tool search, and
agent controls without a machine-readable count owned by that same route.
