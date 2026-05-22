# Checkpoint 290 - Tool Result Mode Count Contract

## Goal
Make structured parser coverage and raw-only preservation visible from aggregate tool-flow coverage.

## Changes
- Added `/qa/tool-flow-coverage.structuredResultModeCount`.
- Added `rawResultModeCount` and `resultModeCountParity`.
- Mirrored result-mode counts/parity into `/qa/coverage-index.groups.toolsAndParsers`.
- Strengthened `scripts/tool-flow-coverage-proof.py`, `scripts/coverage-index-proof.py`, and `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red tool-flow proof failed because the aggregate exposed total tool and callback counts but not structured-vs-raw result-mode counts. The green path derives counts from the same tool registry rows used by the focused registry proof and verifies the counts cover all registered tools.
