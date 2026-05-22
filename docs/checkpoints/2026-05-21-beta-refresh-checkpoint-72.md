# Checkpoint 72 - Chat Scroll And Reasoning Visual Proof

## Changes

- Added `scripts/visual-chat-interaction-proof.py`.
- Added QA route `/qa/chat-visual-mode`.
- Added QA-only chat state controls for:
  - scroll locked;
  - scroll paused with new-output indicator;
  - reasoning expanded;
  - reasoning collapsed.
- Routed QA state through `ContentView`, `ChatPanelView`, `ChatBubble`, and
  `ReasoningBlock` without changing normal user interaction defaults.

## Artifacts

- `docs/visual-proofs/checkpoint-72/chat-scroll-locked-reasoning-expanded.png`
- `docs/visual-proofs/checkpoint-72/chat-scroll-paused-reasoning-expanded.png`
- `docs/visual-proofs/checkpoint-72/chat-scroll-locked-reasoning-collapsed.png`
- `docs/visual-proofs/checkpoint-72/chat-scroll-paused-reasoning-collapsed.png`
- `docs/visual-proofs/checkpoint-72/manifest.json`

## Verified

- Red first: `python3 scripts/visual-chat-interaction-proof.py` failed on
  missing `/qa/chat-visual-mode`.
- Green: `python3 scripts/visual-chat-interaction-proof.py`
- Visual inspection of all four checkpoint-72 screenshots.

## Notes

- This checkpoint proves deterministic chat scroll lock/paused and reasoning
  expanded/collapsed visual states. Settings model warning/cache status and
  real-engine cache metric screenshots remain separate gates.
