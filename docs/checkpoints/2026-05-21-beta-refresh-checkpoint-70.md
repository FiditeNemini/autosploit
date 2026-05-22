# Checkpoint 70 - Nested Lifecycle Visual Proof

## Changes

- Extended `scripts/visual-tab-proof.py` to capture nested lifecycle subtabs.
- Added QA-only `/qa/visual-subtab` route for deterministic visual selection.
- Added optional forced-subtab wiring to Network, Creds, Exploit, Post, and
  OSINT tab views.
- Exposed `qaVisualSubtabs` in `/state` so the proof can assert the selected
  tab/subtab before capturing the app window.

## Artifacts

- `docs/visual-proofs/checkpoint-70/network-capture-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/network-mitm-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/network-tunnels-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/creds-cracking-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/creds-online-brute-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/creds-secrets-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/exploit-reverse-shells-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/exploit-custom-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/exploit-c2-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/post-privesc-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/post-ad-attacks-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/post-lateral-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/osint-username-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/osint-email-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/osint-metadata-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/osint-screenshots-lifecycle.png`
- `docs/visual-proofs/checkpoint-70/manifest.json`

## Verified

- Red first: `python3 scripts/visual-tab-proof.py` failed on missing
  `/qa/visual-subtab`.
- Green: `python3 scripts/visual-tab-proof.py`
- Visual inspection of:
  - `docs/visual-proofs/checkpoint-70/network-capture-lifecycle.png`
  - `docs/visual-proofs/checkpoint-70/exploit-c2-lifecycle.png`
  - `docs/visual-proofs/checkpoint-70/osint-metadata-lifecycle.png`

## Notes

- This checkpoint proves nested lifecycle-strip visual states. Chat
  approval/tool-card visual states remain separate visual gates.
