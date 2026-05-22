# Checkpoint 314 - Tool Flow Proof Maps Aggregate

## Goal

Make the top-level coverage index preserve exact proof maps for tool-flow tab
activity statuses and model-tool visual surfaces.

## Changes

- Added `tabActivityStatusProofs` to `/qa/coverage-index.groups.toolsAndParsers`.
- Added `toolVisualSurfaceProofs` to `/qa/coverage-index.groups.toolsAndParsers`.
- Extended `scripts/coverage-index-proof.py` to compare those maps against
  `/qa/tool-flow-coverage`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` to include the same aggregate
  proof-map checks.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the tools/parsers aggregate exposed
tool-flow status and visual surface proof count/parity, but not the
status-to-proof and surface-to-proof maps themselves. The green path keeps tool
activity visuals and model-tool UI surfaces traceable from the top-level QA
index to their detailed proof scripts.
