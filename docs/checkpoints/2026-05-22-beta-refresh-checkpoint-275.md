# Checkpoint 275 - Chat Header Cache Session Badges

## Goal
Make the chat header visibly distinguish preserved prefix/L2/TurboQuant cache state and the new-context cache-session boundary.

## Changes
- Added `prefix/l2/tq` and `new ctx keeps cache` badges to the chat header when the engine is running with TurboQuant cache stats.
- Added `/state.qaChatVisual.headerBadges`, `cacheSessionIndicator`, and `newContextSessionBoundary` so the visible header contract is machine-readable.
- Updated `scripts/visual-chat-proof.py` to require the visible cache-session badges and refreshed the visual manifest note.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/visual-chat-proof.py`
- `python3 scripts/context-window-cache-proof.py`
- `python3 scripts/chat-new-context-confirm-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red visual-chat proof failed because `/state.qaChatVisual` did not expose the header cache-session badges. The green path wires those badges into the SwiftUI header and the QA state used by the screenshot proof.
