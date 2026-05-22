# Checkpoint 179 - Creds Subtab State

## Goal

Move Creds subtab selection onto the shared AppState-backed path so Cracking,
Online Brute, Secrets, and Vault can be selected and asserted from QA.

## Changes

- Added `scripts/creds-subtab-state-proof.py`.
- Added Creds subtabs to the shared `validSubtabs(for:)` registry.
- Added Creds default active subtab to `/state.activeSubtabs`.
- Wired `CredsTabView` subtab selection through AppState.
- Preserved forced visual subtab compatibility for lifecycle screenshot proofs.

## Proof

```bash
python3 scripts/creds-subtab-state-proof.py
python3 scripts/creds-copy-actions-proof.py
python3 scripts/creds-action-results-proof.py
python3 scripts/network-subtab-state-proof.py
python3 scripts/recon-subtab-state-proof.py
python3 scripts/web-subtab-state-proof.py
python3 scripts/visual-tab-proof.py
```

## Notes

`/qa/tool-subtab` now supports strict user-facing selection for Web, Recon,
Network, and Creds. Invalid Creds subtabs are rejected and recorded in
`/state.subtabActions`.
