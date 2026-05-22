# Checkpoint 133: Creds Copy Actions

Date: 2026-05-22

## Changes

- Added `CredsCopyActionState` and `/state.credsCopyActions` so Creds copy
  controls expose copied kind, count, clipboard preview, and summary.
- Routed Creds toolbar and row/context-menu copy operations through AppState
  for Cracking, Online Brute, Secrets, and Vault.
- Added QA seed/copy routes:
  - `POST /qa/seed-creds-copy-actions`
  - `POST /qa/creds-copy`
- Added `scripts/creds-copy-actions-proof.py`, which starts the app test
  server, seeds representative cracked, brute-force, and secret findings, copies
  each supported Creds subtab, and verifies copy state plus Creds tab activity.
- Updated the system review and flow inventory docs to include the new Creds
  copy proof surface.

## Verification

- `python3 scripts/creds-copy-actions-proof.py`
- `python3 scripts/creds-action-results-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`
