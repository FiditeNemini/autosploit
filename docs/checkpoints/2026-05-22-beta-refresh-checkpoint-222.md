# Checkpoint 222 - Visual Coverage Actual Capture Count

## Goal

Make `/qa/visual-coverage` expose the actual checked-in screenshot capture
count behind the visual proof manifests.

## Changes

- Strengthened `scripts/visual-coverage-proof.py` to require
  `actualCaptureCount`.
- Updated `GET /qa/visual-coverage` with the current checked-in capture count.
- Strengthened `scripts/app-qa-matrix-smoke-proof.py` so the top-level matrix
  catches missing visual capture accounting.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/visual-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/visual-coverage` exposed a minimum capture
threshold but not the actual screenshot count. The green path makes the
checked-in visual breadth auditable from the aggregate route.
