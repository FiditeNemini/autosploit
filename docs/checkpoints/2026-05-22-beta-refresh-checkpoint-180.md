# Checkpoint 180 - Exploit Subtab State

## Goal

Move Exploit subtab selection onto the shared AppState-backed path so
Metasploit, Reverse Shells, Custom, and C2 (Sliver) can be selected and asserted
from QA.

## Changes

- Added `scripts/exploit-subtab-state-proof.py`.
- Added Exploit subtabs to the shared `validSubtabs(for:)` registry.
- Added Exploit default active subtab to `/state.activeSubtabs`.
- Wired `ExploitTabView` subtab selection through AppState.
- Preserved forced visual subtab compatibility for lifecycle screenshot proofs.

## Proof

```bash
python3 scripts/exploit-subtab-state-proof.py
python3 scripts/exploit-copy-actions-proof.py
python3 scripts/exploit-action-differentiation-proof.py
python3 scripts/creds-subtab-state-proof.py
python3 scripts/network-subtab-state-proof.py
python3 scripts/visual-tab-proof.py
```

## Notes

`/qa/tool-subtab` now supports strict user-facing selection for Web, Recon,
Network, Creds, and Exploit. Invalid Exploit subtabs are rejected and recorded in
`/state.subtabActions`.
