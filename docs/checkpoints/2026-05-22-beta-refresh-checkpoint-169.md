# Beta Refresh Checkpoint 169

## Scope

- Prove reasoning-box minimize/expand state is AppState-owned and visible to
  `/state`, not only local SwiftUI state.
- Keep the existing visual chat interaction proof for locked/paused scroll and
  reasoning expanded/collapsed states passing.

## Changes

- Added `collapsedReasoningMessageIDs` to `AppState`.
- Added `recordReasoningBlockCollapsed(_:)`.
- Wired `ChatPanelView`, `ChatBubble`, and `ReasoningBlock` so the reasoning
  header button can report collapse/expand through AppState.
- Added `/qa/seed-chat-reasoning-collapse` and `/qa/chat-reasoning-collapse`.
- Added `/state.qaChatVisual.reasoningBlock` with collapsed state, visible
  chars, and total chars.
- Added `scripts/chat-reasoning-collapse-proof.py`.

## Proof

- Red proof first:
  `python3 scripts/chat-reasoning-collapse-proof.py` failed because
  `/qa/seed-chat-reasoning-collapse` did not exist.
- Green proof:
  `python3 scripts/chat-reasoning-collapse-proof.py` passed.
- Visual regression:
  `python3 scripts/visual-chat-interaction-proof.py` passed.
- Build proof:
  `swift build --package-path ExploitBot` passed.

