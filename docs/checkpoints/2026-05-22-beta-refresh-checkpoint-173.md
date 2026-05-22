# Checkpoint 173 - CVE Add Panel State

## Goal

Make the Settings CVE custom-add panel AppState-owned and proofable, so local
CVE catalogue edits have observable open, cancel, and save state.

## Changes

- Added `scripts/cve-settings-add-panel-proof.py`.
- Added AppState-owned CVE add-panel visibility.
- Added `/qa/cve-settings-add-panel` with `open`, `cancel`, and `save`.
- Extended `/state.cveSettingsActions` with `addPanelVisible`.
- Routed the Settings CVE `+ Add CVE` panel visibility and save action through
  AppState while preserving the existing `addCustomCVEFromSettings` save path.

## Proof

```bash
python3 scripts/cve-settings-add-panel-proof.py
python3 scripts/cve-settings-actions-proof.py
python3 scripts/cve-settings-status-proof.py
```

## Notes

The CVE import, full sync, search, custom-add, and settings status proofs remain
green after making the custom-add panel state observable.
