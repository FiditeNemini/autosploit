# Checkpoint 151 - Finding Wizard Submit

## Scope

- Route the visible finding-wizard submit action through AppState instead of
  creating findings directly from the SwiftUI view.

## Changes

- Added `FindingWizardSubmission` as the typed handoff from the modal to
  AppState.
- Added `AppState.submitFindingWizard(_:)`, which creates the finding,
  dismisses the wizard, updates `/state.reportFindingActions`, updates Report
  tab activity, and logs activity-feed state.
- Routed `FindingWizardView` submit through a callback supplied by
  `ContentView`.
- Added deterministic QA route `/qa/finding-wizard-submit`.
- Added `scripts/finding-wizard-submit-proof.py`.

## Verification

- `python3 scripts/finding-wizard-submit-proof.py`
- `python3 scripts/report-finding-actions-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies finding count, wizard dismissal, last created ID, action
  state, and activity-feed visibility for the modal submit path.
