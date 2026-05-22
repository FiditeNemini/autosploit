# Checkpoint 289 - Tool Schema Cap Contract

## Goal
Make dynamic tool-schema selection visible in aggregate tool-flow coverage.

## Changes
- Added `/qa/tool-flow-coverage.toolSchemaCap`.
- Added `toolSchemaPolicy` and `toolCatalogRoute`.
- Added `/qa/tool-catalog` and `tool-catalog-proof.py` to the tool-flow aggregate contract.
- Mirrored schema cap, policy, and route into `/qa/coverage-index.groups.toolsAndParsers`.
- Strengthened `scripts/tool-flow-coverage-proof.py`, `scripts/coverage-index-proof.py`, and `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red tool-flow proof failed because `/qa/tool-flow-coverage` did not include the dynamic `/qa/tool-catalog` route or a machine-readable schema cap/policy. The green path exposes the prompt/tab-ranked installed-tool policy capped at 12 schemas, so the aggregate proves the app is not force-sending the full tool catalogue.
