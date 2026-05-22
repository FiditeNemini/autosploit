# Checkpoint 147 - CVE Settings Actions

## Scope

- Make Settings > CVE Database Quick Import, Full NVD Sync, Search, and custom
  CVE Save controls route through AppState and expose action telemetry.

## Changes

- Added `CVESettingsActionState` and exposed it as
  `/state.cveSettingsActions`.
- Added deterministic QA route `/qa/cve-settings-action`.
- Routed `CVESettingsView` action buttons through AppState callbacks supplied by
  `SettingsView`.
- Added testing-mode deterministic CVE mutations for action proofs; production
  mode still calls the real `CVEService` import/search/custom-save paths.
- Added `scripts/cve-settings-actions-proof.py`.

## Verification

- `python3 scripts/cve-settings-actions-proof.py`
- `python3 scripts/cve-settings-status-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies action name, query/id, result count, progress text, state
  exposure, and visible activity-feed entries for each CVE settings action.
