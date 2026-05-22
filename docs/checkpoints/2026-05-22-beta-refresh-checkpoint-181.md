# Checkpoint 181 - Post Subtab State

## Goal

Move Post Exploit subtab selection onto the shared AppState-backed path so
PrivEsc, AD Attacks, and Lateral can be selected and asserted from QA.

## Changes

- Added `scripts/post-subtab-state-proof.py`.
- Added Post subtabs to the shared `validSubtabs(for:)` registry.
- Added Post default active subtab to `/state.activeSubtabs`.
- Wired `PostExploitTabView` subtab selection through AppState.
- Preserved forced visual subtab compatibility for lifecycle screenshot proofs.

## Proof

```bash
python3 scripts/post-subtab-state-proof.py
python3 scripts/post-copy-actions-proof.py
python3 scripts/post-attribution-proof.py
python3 scripts/exploit-subtab-state-proof.py
python3 scripts/visual-tab-proof.py
```

## Notes

`/qa/tool-subtab` now supports strict user-facing selection for Web, Recon,
Network, Creds, Exploit, and Post. Invalid Post subtabs are rejected and recorded
in `/state.subtabActions`.
