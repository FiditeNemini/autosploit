# Checkpoint 164 - Stash Filters

## Scope

- Route Stash type filters through AppState and prove filtered Stash state is
  observable alongside add/copy/send/delete actions.

## Changes

- Added AppState-owned `stashActiveFilter`.
- Added `selectedFilter` and `onFilter` wiring to `StashTabView`.
- Added `/qa/stash-filter` and `recordStashFilter(_:)`.
- Extended `/state.stashActions` with active filter and filtered count.
- Extended `scripts/stash-actions-proof.py` to cover filter state.
- Updated the app flow inventory and system review docs.

## Verification

- `python3 scripts/stash-actions-proof.py`
- `python3 scripts/stash-row-context-actions-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- Filter actions update Stash tab activity with `filter_stash`, so visible
  filter changes now participate in the same tab activity/proof model as other
  Stash controls.
