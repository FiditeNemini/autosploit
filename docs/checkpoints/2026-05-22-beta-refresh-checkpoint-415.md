# Beta Refresh Checkpoint 415

## Goal

Make the model-visible tool catalogue auditable beyond total counts by exposing
tab ownership, callback/global visibility, execution, and parser mode detail as
route-owned parity data.

## Changes

- Added `scripts/tool-catalog-detail-proof.py`.
- Extended `/qa/tool-coverage` with tab tool maps/counts, callback tool
  lists/counts, always-visible tool lists/counts, execution counts, result-mode
  counts, and parity flags.
- Mirrored those registry details into
  `/qa/coverage-index.groups.toolsAndParsers`.
- Added the detail proof to `/qa/tool-flow-coverage` and the tools/parsers
  aggregate proof list.
- Updated the system review and flow inventory docs with the detail contract.

## Proof

- `python3 scripts/tool-catalog-detail-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/tool-coverage` exposed row data but not the
durable tab/callback/visibility/execution/result-mode parity fields. The green
path makes the dynamic prompt/tab-ranked catalogue measurable without forcing
the entire tool list into every model turn.
