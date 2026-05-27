# Beta Refresh Checkpoint 434

## Goal

Add a context flow matrix so every retrieval source and delivery mode is tied to
proof files, context coverage, agent-flow source coverage, and the agent-loop
context phase.

## Changes

- Added `scripts/context-flow-matrix-proof.py`.
- Added `/qa/context-flow-matrix`.
- Added `/qa/context-flow-matrix` to `/state.qaCoverage.stateRoutes`.
- Added a context flow matrix snapshot with one row per retrieval source and
  one row per delivery mode.
- Linked each row to `/qa/context-coverage`, `/qa/agent-flow-inventory`,
  `/qa/agent-loop-phase-matrix`, context state keys, proof-owner file
  existence, and `retrieveDynamicContext`.
- Mirrored `contextFlowMatrixRetrievalSourceCount`,
  `contextFlowMatrixDeliveryModeCount`,
  `contextFlowMatrixProofOwnerFileParity`, and
  `contextFlowMatrixProofFileParity` into
  `/qa/coverage-index.groups.chatAndContext`.
- Updated coverage-index and app matrix proofs to require the new context flow
  matrix route and mirror.
- Updated the system review and flow inventory docs with the context flow
  matrix contract.

## Proof

- `python3 scripts/context-flow-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/context-flow-matrix` did not exist. The green
path keeps context retrieval and delivery paths tied to source coverage,
agent-loop context phase ownership, docs, and proof-owner files.
