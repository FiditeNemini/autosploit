# Checkpoint 182 - OSINT Subtab State

## Goal

Move OSINT subtab selection onto the shared AppState-backed path so Username,
Email, Metadata, and Screenshots can be selected and asserted from QA.

## Changes

- Added `scripts/osint-subtab-state-proof.py`.
- Added OSINT subtabs to the shared `validSubtabs(for:)` registry.
- Added OSINT default active subtab to `/state.activeSubtabs`.
- Wired `OSINTTabView` subtab selection through AppState.
- Preserved forced visual subtab compatibility for lifecycle screenshot proofs.

## Proof

```bash
python3 scripts/osint-subtab-state-proof.py
python3 scripts/osint-copy-actions-proof.py
python3 scripts/osint-artifact-actions-proof.py
python3 scripts/osint-screenshot-artifact-proof.py
python3 scripts/visual-tab-proof.py
```

## Notes

`/qa/tool-subtab` now supports strict user-facing selection for Web, Recon,
Network, Creds, Exploit, Post, and OSINT. Invalid OSINT subtabs are rejected and
recorded in `/state.subtabActions`.
