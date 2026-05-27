# Beta Refresh Checkpoint 432

## Goal

Add a per-phase agentic loop matrix so every loop phase is tied to source
coverage, proof files, state keys, routes, authorization policy, and tool
execution coverage.

## Changes

- Added `scripts/agent-loop-phase-matrix-proof.py`.
- Added `/qa/agent-loop-phase-matrix`.
- Added `/qa/agent-loop-phase-matrix` to `/state.qaCoverage.stateRoutes`.
- Added an agent-loop phase matrix snapshot that records each loop phase,
  phase proofs, linked source phases from `/qa/agent-flow-inventory`,
  authorization policy map, state keys, visual state keys, loop routes,
  agent-flow function count, and per-tool execution matrix count.
- Mirrored `agentLoopPhaseMatrixCount`, `agentLoopPhaseMatrixParity`,
  `agentLoopPhaseMatrixSourceCoverageParity`, and
  `agentLoopPhaseMatrixProofFileParity` into
  `/qa/coverage-index.groups.tabsAndSessions`.
- Updated coverage-index and app matrix proofs to require the new per-phase
  route and mirror.
- Updated the system review and flow inventory docs with the agent-loop phase
  matrix contract.

## Proof

- `python3 scripts/agent-loop-phase-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/agent-loop-phase-matrix` did not exist. The
green path makes each agentic loop phase auditable against source-token
coverage, mode policy, state keys, routes, per-tool execution coverage, and
proof-file parity.
