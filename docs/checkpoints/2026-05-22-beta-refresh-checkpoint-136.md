# Checkpoint 136 - OSINT Copy Action State

## Scope

- Close the OSINT copy-control gap with AppState-routed copy actions and proof
  coverage.

## Changes

- Added `OSINTCopyActionState` and `/state.osintCopyActions` with copied kind,
  status, count, clipboard preview, and summary.
- Added deterministic QA routes:
  - `/qa/seed-osint-copy-actions`
  - `/qa/osint-copy`
- Routed OSINT toolbar and row context-menu copy controls through
  `recordOSINTCopy`, preserving clipboard behavior while updating tab activity
  as `copy_osint`.
- Tightened email-row classification so metadata rows do not appear in Email
  copy/view output.
- Added `scripts/osint-copy-actions-proof.py`.

## Verification

- `python3 scripts/osint-copy-actions-proof.py`
- `python3 scripts/osint-artifact-actions-proof.py`
- `python3 scripts/osint-screenshot-artifact-proof.py`
- `swift build --package-path ExploitBot`

## Notes

- The proof covers username, email, metadata, screenshots, and all-row OSINT
  copy actions using deterministic rows and a local screenshot fixture.
