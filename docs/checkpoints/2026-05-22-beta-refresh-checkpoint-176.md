# Checkpoint 176 - Web Subtab State

## Goal

Start moving real tool subtab selection out of local-only view state and into
AppState so tool surfaces can be navigated, asserted, and documented from QA.

## Changes

- Added `scripts/web-subtab-state-proof.py`.
- Added `SubtabActionState` and exposed it as `/state.subtabActions`.
- Added `/state.activeSubtabs`.
- Added `/qa/tool-subtab` for strict user-facing subtab selection.
- Wired Web tab subtab selection through AppState.
- Preserved `/qa/visual-subtab` as a visual-proof forcing route for lifecycle
  subtabs that are not yet fully AppState-backed.

## Proof

```bash
python3 scripts/web-subtab-state-proof.py
python3 scripts/tab-switch-action-proof.py
python3 scripts/visual-tab-proof.py
```

## Notes

`/qa/tool-subtab` validates known Web subtabs and rejects invalid values.
`/qa/visual-subtab` remains compatibility-oriented for screenshot coverage
across Network, Creds, Exploit, Post, and OSINT lifecycle subtabs.
