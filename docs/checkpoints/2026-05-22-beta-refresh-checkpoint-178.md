# Checkpoint 178 - Network Subtab State

## Goal

Move Network subtab selection onto the shared AppState-backed path so protocol,
SNMP, capture, MITM, and tunnel surfaces can be selected and asserted from QA.

## Changes

- Added `scripts/network-subtab-state-proof.py`.
- Added Network subtabs to the shared `validSubtabs(for:)` registry.
- Added Network default active subtab to `/state.activeSubtabs`.
- Wired `NetworkTabView` subtab selection through AppState.
- Preserved forced visual subtab compatibility for lifecycle screenshot proofs.

## Proof

```bash
python3 scripts/network-subtab-state-proof.py
python3 scripts/network-copy-actions-proof.py
python3 scripts/network-protocol-action-proof.py
python3 scripts/recon-subtab-state-proof.py
python3 scripts/web-subtab-state-proof.py
python3 scripts/visual-tab-proof.py
```

## Notes

`/qa/tool-subtab` now supports strict user-facing selection for Web, Recon, and
Network. Invalid Network subtabs are rejected and recorded in
`/state.subtabActions`.
