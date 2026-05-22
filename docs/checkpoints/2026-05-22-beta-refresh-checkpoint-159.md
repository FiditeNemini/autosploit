# Checkpoint 159 - Report Export Actions

## Scope

- Route the visible Report tab PDF and Markdown export buttons through AppState
  and prove they update export state, artifacts, and activity feedback.

## Changes

- Added `/qa/report-export-action` for proof-driven export action testing.
- Added `exportReportArtifacts(action:outputDirectory:)` and
  `exportReportArtifactsFromUI(action:)` in AppState.
- Added PDF and Markdown export callbacks to `ReportTabView` and wired them
  from `ContentView`.
- Added `scripts/report-visible-export-actions-proof.py`.
- Updated the app flow inventory and system review docs with the visible export
  proof coverage.

## Verification

- `python3 scripts/report-visible-export-actions-proof.py`
- `python3 scripts/report-export-proof.py`
- `python3 scripts/report-generate-action-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- Visible PDF/Markdown exports use the same artifact writer as the existing QA
  export service, so `/state.reportExport` reports HTML, Markdown, JSON, and
  PDF artifacts for both toolbar actions.
