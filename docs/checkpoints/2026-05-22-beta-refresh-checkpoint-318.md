# Checkpoint 318 - Session Workflow Proof Map Aggregate

## Goal

Make the top-level coverage index preserve the workflow-surface proof map from
`/qa/session-coverage`.

## Changes

- Added `sessionWorkflowSurfaceProofs` to
  `/qa/coverage-index.groups.tabsAndSessions`.
- Extended `scripts/coverage-index-proof.py` to compare the aggregate workflow
  proof map against `/qa/session-coverage`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` to include the same aggregate
  workflow proof-map check.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the tabs/sessions aggregate exposed
session workflow surfaces plus proof count/parity, but not the surface-to-proof
map itself. The green path keeps onboarding, sidebar, overlay, model picker,
persistence, finding wizard, tab/phase navigation, and activity feed workflows
traceable from the top-level QA index to their proof scripts.
