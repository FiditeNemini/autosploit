# Beta Refresh Checkpoint 430

## Goal

Add a single source-owned cross-flow inventory that proves every primary tab is
wired to its view, tools, action proofs, subtab contract, function inventory,
and agent-loop phases.

## Changes

- Added `scripts/tab-tool-function-flow-proof.py`.
- Added `/qa/tab-tool-function-flow`.
- Added `/qa/tab-tool-function-flow` to `/state.qaCoverage.stateRoutes`.
- Added a tab/tool/function flow snapshot that records each `ToolTab` row with
  its SwiftUI view, tab tools, action surface proofs, subtab proof/count,
  `/qa/function-flow-inventory` count, and agent-loop phases.
- Mirrored `tabToolFunctionFlowCount`, `tabToolFunctionFlowParity`,
  `tabToolFunctionFlowProofFileParity`, `tabToolFunctionFlowFunctionCount`,
  and `tabToolFunctionFlowAgentLoopPhaseCount` into
  `/qa/coverage-index.groups.tabsAndSessions`.
- Updated coverage-index and app matrix proofs to require the new cross-flow
  route and mirror.
- Updated the system review and flow inventory docs with the tab/tool/function
  flow contract.

## Proof

- `python3 scripts/tab-tool-function-flow-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/tab-tool-function-flow` did not exist. The
green path ties the app's primary tab surface to the existing tool, action,
subtab, view, function, and agent-loop inventories so tab coverage is checked
as one flow instead of as unrelated route fragments.
