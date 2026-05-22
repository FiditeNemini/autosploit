# Checkpoint 224 - Settings Visual Index Counts

## Goal

Make `/qa/coverage-index.groups.settingsAndVisuals` expose the visual manifest
and screenshot capture counts already proven by `/qa/settings-coverage` and
`/qa/visual-coverage`.

## Changes

- Strengthened `scripts/coverage-index-proof.py` to require settings visual
  manifest count, full visual manifest count, and actual screenshot capture
  count on the settings/visuals group.
- Updated `GET /qa/coverage-index` so `settingsAndVisuals` includes
  `settingsVisualManifestCount`, `visualManifestCount`, and
  `actualCaptureCount`.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/settings-coverage-proof.py`
- `python3 scripts/visual-coverage-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because the settings/visuals group only exposed endpoint
and proof accounting. The green path keeps the focused settings and visual
coverage routes as the source of detailed proof data while making their manifest
and capture breadth visible from the top-level QA index.
