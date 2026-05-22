# Checkpoint 356 - Agent Loop State Keys

## Goal

Make `/qa/coverage-index.groups.tabsAndSessions` preserve the concrete
agent-loop state-key list reported by `/qa/agent-loop-coverage`.

## Changes

- Added `agentLoopStateKeys` to the tabs/sessions coverage-index aggregate.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py` to compare the list against
  `/qa/agent-loop-coverage`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because the top-level tabs/sessions aggregate preserved
the agent-loop state-key count but not the actual state-key list that names the
chat, agent, result, activity-feed, mode, context, and tool-schema surfaces used
by the agentic loop.
