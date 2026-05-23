# Beta Refresh Checkpoint 421

## Goal

Expose a source-owned SwiftUI view inventory so every visible app view surface
is grouped, documented, mirrored into coverage, and tied to a proof owner.

## Changes

- Added `scripts/view-inventory-proof.py`.
- Added `/qa/view-inventory`.
- Added `/qa/view-inventory` to `/state.qaCoverage.stateRoutes`.
- Added source parsing for SwiftUI `View` structs under
  `ExploitBot/Sources/ExploitBot/App` and `Views`.
- Added grouping and proof-owner mapping for app shell, chat, tabs, settings,
  navigation, overlays, and panels.
- Added a source-checked main `ToolTab` to tab-view map.
- Mirrored view file counts, view struct counts, group counts, main tab map,
  main tab parity, and proof-file parity into
  `/qa/coverage-index.groups.appState`.
- Updated coverage-index and app matrix proofs to require the view inventory
  endpoint and mirror.
- Updated the system review and flow inventory docs with the view inventory
  contract.

## Proof

- `python3 scripts/view-inventory-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/view-inventory` did not exist. The green path
keeps the SwiftUI source tree as the authority and uses coverage-index as the
mirror, so future page, tab, panel, chat, settings, or overlay additions must
appear in the source-derived inventory.
