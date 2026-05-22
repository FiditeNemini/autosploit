# Checkpoint 132: Network Copy Actions

Date: 2026-05-22

## Changes

- Added `NetworkCopyActionState` and `/state.networkCopyActions` so Network
  copy controls expose copied kind, count, clipboard preview, and summary.
- Routed Network toolbar and row/context-menu copy operations through AppState
  for Protocols, SNMP, Capture, MITM, and Tunnels.
- Added QA seed/copy routes:
  - `POST /qa/seed-network-copy-actions`
  - `POST /qa/network-copy`
- Added `scripts/network-copy-actions-proof.py`, which starts the app test
  server, seeds representative Network rows/raw outputs, copies each supported
  Network subtab, and verifies copy state plus Network tab activity.
- Updated the system review and flow inventory docs to include the new Network
  copy proof surface.

## Verification

- `python3 scripts/network-copy-actions-proof.py`
- `python3 scripts/network-protocol-action-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`
