# Beta Refresh Checkpoint 431

## Goal

Add a per-tool execution matrix so every individual tool is tied to its
execution handler, result mode, authorization behavior, source hooks, and
coverage-index mirror.

## Changes

- Added `scripts/tool-execution-matrix-proof.py`.
- Added `/qa/tool-execution-matrix`.
- Added `/qa/tool-execution-matrix` to `/state.qaCoverage.stateRoutes`.
- Added a tool execution matrix snapshot that records every registry tool's
  binary, argument count, callback/subprocess execution path, result mode,
  owning tabs, source hooks, execution states, and manual/copilot/autopilot
  authorization policies.
- Mirrored `toolExecutionMatrixCount`, `toolExecutionMatrixParity`,
  `toolExecutionMatrixProofFileParity`,
  `toolExecutionMatrixAuthorizationPolicyCount`,
  `toolExecutionMatrixExecutionStateCount`, and
  `toolExecutionMatrixSourceHookParity` into
  `/qa/coverage-index.groups.toolsAndParsers`.
- Updated coverage-index and app matrix proofs to require the new per-tool
  execution matrix route and mirror.
- Updated the system review and flow inventory docs with the tool execution
  matrix contract.

## Proof

- `python3 scripts/tool-execution-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/tool-execution-matrix` did not exist. The
green path keeps per-tool execution coverage tied to the registry, tool-flow
route, authorization route, source hooks, and coverage index instead of relying
only on aggregate callback/subprocess counts.
