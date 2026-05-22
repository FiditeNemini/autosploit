# Checkpoint 183 - Report Subtab State

## Goal

Move Report subtab selection onto the shared AppState-backed path so Findings
and Preview can be selected and asserted from QA.

## Changes

- Added `scripts/report-subtab-state-proof.py`.
- Added Report subtabs to the shared `validSubtabs(for:)` registry.
- Added Report default active subtab to `/state.activeSubtabs`.
- Wired `ReportTabView` subtab selection through AppState.
- Routed Generate/Preview transitions through the shared subtab callback.

## Proof

```bash
python3 scripts/report-subtab-state-proof.py
python3 scripts/report-generate-action-proof.py
python3 scripts/report-agent-action-proof.py
python3 scripts/report-export-proof.py
python3 scripts/report-visible-export-actions-proof.py
rg -n "SubtabBar\\(|@State private var activeSubtab" ExploitBot/Sources/ExploitBot
python3 scripts/visual-tab-proof.py
```

## Notes

Every visible `SubtabBar` now uses `activeSubtabBinding`; no local
`@State private var activeSubtab` remains. `/qa/tool-subtab` now supports strict
user-facing selection for Web, Recon, Network, Creds, Exploit, Post, OSINT, and
Report.
