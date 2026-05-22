# Checkpoint 131: Recon Copy Actions

Date: 2026-05-22

## Changes

- Added `ReconCopyActionState` and `/state.reconCopyActions` so Recon copy
  controls expose the copied kind, count, clipboard preview, and summary.
- Routed Recon toolbar and row context-menu copy operations through AppState for
  Subdomains, Ports, Web Hosts, Crawl, and OSINT.
- Added QA seed/copy routes:
  - `POST /qa/seed-recon-copy-actions`
  - `POST /qa/recon-copy`
- Added `scripts/recon-copy-actions-proof.py`, which starts the app test server,
  seeds representative Recon rows, copies each supported Recon subtab, and
  verifies copy state plus Recon tab activity.
- Updated the system review and flow inventory docs to include the new Recon
  copy proof surface.

## Verification

- `python3 scripts/recon-copy-actions-proof.py`
- `python3 scripts/recon-action-status-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`
