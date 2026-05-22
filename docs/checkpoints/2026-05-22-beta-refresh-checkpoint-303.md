# Checkpoint 303 - Tool Visual Surface Proof Map

## Goal
Tie each model-tool visual surface to concrete proof scripts.

## Changes
- Added `/qa/tool-flow-coverage.toolVisualSurfaceProofs`.
- Added `toolVisualSurfaceProofCount` and `toolVisualSurfaceProofParity`.
- Mirrored visual-surface proof count/parity into
  `/qa/coverage-index.groups.toolsAndParsers`.
- Added the relevant visual/action proofs to the tool-flow proof set.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`

## Notes
The red tool-flow proof failed because `/qa/tool-flow-coverage` named chat tool
cards, activity-feed status, tab indicators, parsed result rows, context hits,
and expandable tool output without mapping those surfaces to the scripts that
prove them. The green path adds that map and mirrors proof count/parity through
the coverage index.
