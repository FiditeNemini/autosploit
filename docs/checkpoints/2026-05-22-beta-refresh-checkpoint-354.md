# Checkpoint 354 - Tool Flow Registry Counters

## Goal

Make `/qa/coverage-index.groups.toolsAndParsers` preserve the registry counters
reported by `/qa/tool-flow-coverage`.

## Changes

- Added `toolFlowToolCount` and `toolFlowCallbackCount` to the
  tools/parsers coverage-index aggregate.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py` to compare those fields against
  `/qa/tool-flow-coverage`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because the top-level tools/parsers aggregate mirrored
tool-flow proofs, routes, families, state keys, contracts, schema policy, result
modes, visual surfaces, and status proof maps, but did not preserve the tool and
callback counts owned by `/qa/tool-flow-coverage`.
