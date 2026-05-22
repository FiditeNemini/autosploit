# Checkpoint 158 - Report Generate Action

## Scope

- Route the visible Report tab Generate button through AppState and expose
  deterministic preview-generation state.

## Changes

- Added `ReportRenderActionState` and exposed it as
  `/state.reportRenderActions`.
- Added `generateReportPreview(template:)`, `seedReportGenerateActionForQA()`,
  and `reportTemplate(named:)` in AppState.
- Added QA routes `/qa/seed-report-generate-action` and
  `/qa/report-generate-action`.
- Added `onGenerateReport` callback to `ReportTabView` and wired it from
  `ContentView`.
- Added `scripts/report-generate-action-proof.py`.

## Verification

- `python3 scripts/report-generate-action-proof.py`
- `python3 scripts/report-export-proof.py`
- `python3 scripts/report-agent-action-proof.py`
- `python3 scripts/report-finding-actions-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies generated HTML length, preview content, finding count,
  action state, and activity-feed visibility.
