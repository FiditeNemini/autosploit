# Checkpoint 334 - Tool Flow Operational Aggregate

## Goal

Make `/qa/coverage-index.groups.toolsAndParsers` preserve the operational
route, proof, family, state-key, and contract fields from
`/qa/tool-flow-coverage`.

## Changes

- Added `toolFlowProofCount`.
- Added `toolFlowRoutes` and `toolFlowRouteCount`.
- Added `toolFlowFamilies` and `toolFlowFamilyCount`.
- Added `toolFlowStateKeys`.
- Added `toolFlowContracts` and `toolFlowContractCount`.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red coverage-index proof failed because the tools/parsers aggregate exposed
tool/schema counts and visual/status proof maps but did not carry the
tool-flow route list, proof count, family list, state-key list, or contract map.
The green path keeps tool/parser loop routing and state ownership visible from
the top-level QA index.
