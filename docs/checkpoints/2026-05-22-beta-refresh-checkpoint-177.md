# Checkpoint 177 - Recon Subtab State

## Goal

Move Recon subtab selection onto the same AppState-backed path as Web so Recon
tables, copy behavior, and visible tool context can be asserted from QA.

## Changes

- Added `scripts/recon-subtab-state-proof.py`.
- Added Recon subtabs to the shared `validSubtabs(for:)` registry.
- Added Recon default active subtab to `/state.activeSubtabs`.
- Wired `ReconTabView` subtab selection through AppState.
- Kept forced visual subtab compatibility for screenshot proofs.

## Proof

```bash
python3 scripts/recon-subtab-state-proof.py
python3 scripts/web-subtab-state-proof.py
python3 scripts/recon-copy-actions-proof.py
python3 scripts/recon-action-status-proof.py
python3 scripts/visual-tab-proof.py
```

## Notes

`/qa/tool-subtab` now supports strict user-facing selection for both Web and
Recon. Invalid Recon subtabs are rejected and recorded in `/state.subtabActions`.
