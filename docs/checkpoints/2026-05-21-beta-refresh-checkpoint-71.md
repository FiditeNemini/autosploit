# Checkpoint 71 - Chat Tool Visual Proof

## Changes

- Added `scripts/visual-chat-proof.py`.
- Added QA route `/qa/seed-chat-visual-states`.
- Seeded deterministic chat state with:
  - visible token metrics;
  - active running-tool header state;
  - streaming reasoning block;
  - copilot approval card;
  - running tool card;
  - failed tool card;
  - Stop button state.
- Updated chat tool status colors so running, failed, rejected, blocked,
  canceled, and ok states are visually distinct.

## Artifacts

- `docs/visual-proofs/checkpoint-71/chat-tool-states.png`
- `docs/visual-proofs/checkpoint-71/manifest.json`

## Verified

- Red first: `python3 scripts/visual-chat-proof.py` failed on missing
  `/qa/seed-chat-visual-states`.
- Green: `python3 scripts/visual-chat-proof.py`
- Visual inspection of
  `docs/visual-proofs/checkpoint-71/chat-tool-states.png`

## Notes

- This checkpoint proves seeded chat approval/tool-card, reasoning, metric, and
  Stop states. Scroll paused/relock and reasoning collapsed/reopened states are
  still separate visual gates.
