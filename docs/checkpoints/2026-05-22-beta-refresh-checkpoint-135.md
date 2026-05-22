# Checkpoint 135: Post Copy Actions

Date: 2026-05-22

## Changes

- Added `PostCopyActionState` and `/state.postCopyActions` so Post copy
  controls expose copied kind, count, clipboard preview, and summary.
- Routed Post toolbar, raw result, compromised-host, and attribution-row copy
  operations through AppState for PrivEsc, AD Attacks, Lateral, and Attribution.
- Added QA seed/copy routes:
  - `POST /qa/seed-post-copy-actions`
  - `POST /qa/post-copy`
- Added `scripts/post-copy-actions-proof.py`, which starts the app test server,
  seeds representative LinPEAS output, impacket output, a compromised lateral
  host, and attribution rows, then verifies copy state plus Post tab activity.
- Updated the system review and flow inventory docs to include the new Post copy
  proof surface.

## Verification

- `python3 scripts/post-copy-actions-proof.py`
- `python3 scripts/post-attribution-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`
