# Checkpoint 69 - Tab Activity Visual Proof

## Changes

- Added `scripts/visual-tab-proof.py`.
- Added the QA route `/qa/seed-visual-activity`.
- The route seeds tab-bar activity states and lifecycle lanes for Web, Network,
  Creds, Exploit, Post, and OSINT.
- The proof script launches the macOS app, cycles the major tool tabs, captures
  cropped screenshots of the ExploitBot window, and verifies that each image is
  non-empty with readable dimensions.

## Artifacts

- `docs/visual-proofs/checkpoint-69/web-activity.png`
- `docs/visual-proofs/checkpoint-69/network-activity.png`
- `docs/visual-proofs/checkpoint-69/creds-activity.png`
- `docs/visual-proofs/checkpoint-69/exploit-activity.png`
- `docs/visual-proofs/checkpoint-69/post-activity.png`
- `docs/visual-proofs/checkpoint-69/osint-activity.png`
- `docs/visual-proofs/checkpoint-69/manifest.json`

## Verified

- `python3 scripts/visual-tab-proof.py`
- Visual inspection of `docs/visual-proofs/checkpoint-69/network-activity.png`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `swift build --package-path ExploitBot`
- `python3 scripts/live-turn-harness.py`
- `git diff --check`

## Notes

- This checkpoint proves top tab-bar activity indicators. Nested lifecycle-strip
  screenshots and chat approval/tool-card visual states are still separate
  visual gates.
