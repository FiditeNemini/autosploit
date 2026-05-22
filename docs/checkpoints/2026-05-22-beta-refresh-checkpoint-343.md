# Checkpoint 343 - App State QA Source Lists

## Goal

Make `/qa/coverage-index.groups.appState` preserve the source `/state.qaCoverage`
route, hook, and subtab proof lists, not only their counts.

## Changes

- Added `stateRoutes` and `stateRouteCount`.
- Added `contextHooks` and `contextHookCount`.
- Added `subtabStateTabs` and `subtabStateTabCount`.
- Added `subtabStateProofs` and `subtabStateProofCount`.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because the app-state aggregate carried source QA counts
but not the named route, hook, tab, or proof lists. The green path keeps the app
route inventory and subtab proof ownership visible from the top-level QA index.
