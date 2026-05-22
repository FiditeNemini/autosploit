# Checkpoint 292 - Tool Visual Surface Contract

## Goal
Make the visible feedback surfaces for model-issued tool actions explicit from
the aggregate tool-flow QA route.

## Changes
- Added `/qa/tool-flow-coverage.toolVisualSurfaces`.
- Added `toolVisualSurfaceCount` and `toolVisualSurfaceParity`.
- Mirrored those fields into `/qa/coverage-index.groups.toolsAndParsers`.
- Strengthened the focused tool-flow proof, coverage-index proof, and broad app
  QA matrix.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red tool-flow proof failed because the aggregate exposed state keys and tab
activity statuses, but not the visible surfaces that prove a tool action is
shown across the chat, Activity Feed, active tab, parsed results, context
catalogue, and tool-output expander. The green path names those surfaces and
checks list/count/parity.
