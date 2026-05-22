# Beta Refresh Checkpoint 168

## Scope

- Prove long tool-output expand/collapse is AppState-owned and visible to the
  QA/status API.
- Keep long tool-call output inspectable without silently hiding the expansion
  state inside local SwiftUI state.

## Changes

- Added `expandedToolMessageIDs` to `AppState`.
- Added `recordToolOutputExpansion(forToolNamed:expanded:)`.
- Wired `ChatPanelView` tool-output show-more/show-less controls through
  `onSetToolOutputExpanded`.
- Added `/qa/seed-chat-tool-output-expand` and `/qa/chat-tool-output-expand`.
- Added `/state.qaChatVisual.toolOutputExpansion` with tool name, expanded
  state, visible lines, hidden lines, and total lines.
- Added `scripts/chat-tool-output-expand-proof.py`.

## Proof

- Red proof first:
  `python3 scripts/chat-tool-output-expand-proof.py` failed because
  `/qa/seed-chat-tool-output-expand` did not exist.
- Green proof:
  `python3 scripts/chat-tool-output-expand-proof.py` passed.
- Regression proof:
  `python3 scripts/visual-chat-proof.py` passed.
- Build proof:
  `swift build --package-path ExploitBot` passed.

## Note

- App-owning proof scripts must run serially. A concurrent visual proof can
  reseed chat state while this proof is between seed and toggle.
