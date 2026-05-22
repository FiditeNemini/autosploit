# Checkpoint 143 - Report Delete Wiring

## Scope

- Ensure the visible Report finding delete button uses AppState report finding
  action telemetry instead of deleting directly through `FindingService`.

## Changes

- Added `onDeleteFinding` to `ReportTabView`.
- Routed Report row delete from `ContentView` to `state.deleteReportFinding`.
- Added `scripts/report-visible-delete-wiring-proof.py`.

## Verification

- `python3 scripts/report-visible-delete-wiring-proof.py`
- `python3 scripts/report-finding-actions-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The wiring proof blocks regressions where the visible delete button bypasses
  `/state.reportFindingActions`; the live proof still verifies created/deleted
  ids and Report tab activity.
