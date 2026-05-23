# Beta Refresh Checkpoint 398

## Goal

Make tool-flow state-key coverage countable and parity-checked from the source route and the top-level tools/parsers coverage group.

## Changes

- Added `stateKeyCount` and `stateKeyParity` to `/qa/tool-flow-coverage`.
- Mirrored `toolFlowStateKeyCount` and `toolFlowStateKeyParity` through `/qa/coverage-index.groups.toolsAndParsers`.
- Strengthened tool-flow, coverage-index, and app QA matrix proofs so model-issued tool calls remain tied to message tool cards, tab activities, activity feed, result rows, and context catalog state.
- Updated the system review and flow inventory documentation with the tool-flow state-key count/parity contract.

## Proof

- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red tool-flow proof failed because `/qa/tool-flow-coverage` listed the state keys but did not expose a count or parity flag. The green path makes the model-tool UI/state handoff measurable from both the source route and aggregate coverage index.
