# Checkpoint 361 - Agent Loop Agent Contract Count

## Goal

Make `/qa/agent-loop-coverage` own the deployed-agent/inheritance contract
count and mirror that count through `/qa/coverage-index.groups.tabsAndSessions`.

## Changes

- Added `agentContractCount` to `/qa/agent-loop-coverage`.
- Added `agentLoopAgentContractCount` to the tabs/sessions coverage-index
  aggregate.
- Extended `scripts/agent-loop-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/agent-loop-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/agent-loop-coverage` exposed the agent
contract map for multi-agent status, forced autopilot, runtime inheritance, and
search-context access without a machine-readable count owned by that route.
