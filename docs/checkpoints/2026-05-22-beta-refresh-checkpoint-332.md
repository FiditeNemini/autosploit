# Checkpoint 332 - Agent Loop Operational Aggregate

## Goal

Make the top-level coverage index preserve the agent-loop operational contracts
from `/qa/agent-loop-coverage`, not only the phase/proof map.

## Changes

- Added `agentLoopModes` to `/qa/coverage-index.groups.tabsAndSessions`.
- Added `agentLoopAgents`, `agentLoopRoutes`, and `agentLoopContracts`.
- Added `agentLoopActionTelemetryFields` and
  `agentLoopActionTelemetryFieldCount`.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py` to compare those aggregate fields
  against `/qa/agent-loop-coverage`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red coverage-index proof failed because the tabs/sessions aggregate exposed
agent-loop phases and phase proofs but not mode behavior, deployed-agent
inheritance/status, route contracts, contract flags, or action telemetry fields.
The green path keeps the agentic loop controls and visible status wiring
auditable from the top-level QA index.
