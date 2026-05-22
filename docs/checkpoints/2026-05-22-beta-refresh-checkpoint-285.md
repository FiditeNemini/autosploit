# Checkpoint 285 - Agent Loop State Surface Contract

## Goal
Make the autonomous agent loop's visible state surfaces machine-auditable from `/qa/agent-loop-coverage` and `/qa/coverage-index`.

## Changes
- Added agent-loop `stateKeys`, `stateKeyCount`, `visualStateKeys`, and `visualStateKeyCount`.
- Covered active agent chat/results/feed routing, `/state.agents`, `/state.agentActions`, context snippet count, and exposed tool schema audit state.
- Mirrored the agent-loop state-key count and visual state keys into `/qa/coverage-index.groups.tabsAndSessions`.
- Strengthened the focused agent-loop proof, broad app QA matrix, and coverage-index proof.
- Updated the flow inventory and system review docs.

## Proof
- `python3 scripts/agent-loop-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red agent-loop proof failed because the route exposed modes, routes, contracts, and telemetry fields, but not the `/state` surfaces that prove full-auto agent behavior is visible through agent selection, active display routing, context audit, and tool schema audit state.
