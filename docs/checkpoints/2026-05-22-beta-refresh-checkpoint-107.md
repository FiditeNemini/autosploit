# Checkpoint 107: Report Agent Draft Loop

## Scope

- Add a Report-tab path that routes report drafting into the same agentic chat
  loop used by the rest of the tool tabs.
- Preserve deterministic direct report generation and artifact export.

## Changes

- Added `ReportActionState` and `/state.reportAction`.
- Added `recordReportAgentDraftAction(...)`, which builds a bounded report
  drafting prompt from confirmed findings and can send it to chat.
- Report tab now has an `Agent Draft` action beside deterministic `Generate`.
- Report tab now renders an `AGENT REPORT QUEUED` status strip with template
  and finding count.
- Added QA seed and proofs for the report agent-draft path.

## Proof

Commands:

```bash
python3 scripts/report-agent-action-proof.py
python3 scripts/visual-report-agent-proof.py
```

Results:

- `/state.reportAction` shows `kind=agentDraft`, `status=queued`,
  `template=Full Pentest Report`, and `findingCount=1`.
- The generated prompt contains the seeded finding and CVE id.
- Report tab activity shows `lastTool=agent_report`.
- Visual artifact:
  `docs/visual-proofs/checkpoint-107/report-agent-queued.png`.

## Boundary

This proves report drafting enters the app's agent/chat loop. It does not
replace deterministic report export proof, and it does not claim real-model
quality for the drafted report.
