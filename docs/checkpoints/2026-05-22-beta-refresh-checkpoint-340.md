# Checkpoint 340 - Settings Visual Aggregate Detail

## Goal

Make `/qa/coverage-index.groups.settingsAndVisuals` preserve detailed Settings
and visual proof metadata from `/qa/settings-coverage` and
`/qa/visual-coverage`.

## Changes

- Added Settings category list/count/current category.
- Added Settings route list/count, contract map/count, proof list/count, and
  visual manifest list/count.
- Added visual route list/count, contract map/count, proof list/count, manifest
  list/count, minimum capture count, and actual capture count.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because the aggregate carried Settings and visual surface
proof maps plus counts, but not the route, contract, proof-list, category, or
manifest details from the detailed endpoints. The green path keeps Settings page
organization and visual capture coverage auditable from the top-level QA index.
