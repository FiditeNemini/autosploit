# Checkpoint 90 - OSINT Screenshot Artifact Preview

## Scope

- Close the OSINT screenshot artifact gap with validated screenshot file
  metadata and visible preview proof.

## Changes

- `OSINTEntry` now carries artifact metadata:
  `artifactPath`, `artifactExists`, `artifactBytes`, and `previewKind`.
- `ResultsStore` validates `gowitness` screenshot files and records image
  artifact metadata instead of only storing raw paths.
- `/state.osintArtifacts` and `/results.osint` now expose OSINT artifact rows
  for proof scripts.
- Added QA route `/qa/seed-osint-screenshot-artifact`, which creates a real
  tiny PNG, selects the OSINT Screenshots subtab, and marks the screenshot
  lifecycle complete.
- `OSINTTabView` renders image thumbnails and byte counts for screenshot
  artifacts.
- Added `scripts/osint-screenshot-artifact-proof.py`.
- Added `scripts/visual-osint-screenshot-proof.py`.

## Proof

- `swift build --package-path ExploitBot`
- `python3 scripts/osint-screenshot-artifact-proof.py`
- `python3 scripts/visual-osint-screenshot-proof.py`
- `python3 scripts/live-turn-harness.py`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`

Visual artifact:

- `docs/visual-proofs/checkpoint-90/osint-screenshot-preview.png`

## Remaining

- Richer row actions for opening/revealing screenshot files can still be added.
