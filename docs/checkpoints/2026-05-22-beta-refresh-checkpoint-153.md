# Checkpoint 153 - Stash Send Chat Control

## Scope

- Route stash send-to-chat and tool-tab command sends through AppState chat
  send telemetry.

## Changes

- `ContentView.sendToChat(_:)` now calls `state.sendChatMessage(...)`.
- Stash tab `onSendToChat` now calls `state.sendChatMessage(...)` with bounded
  content.
- `recordStashSend(item:)` now routes through `sendChatMessage(...)` before
  updating `/state.stashActions`.
- Added `scripts/stash-send-chat-control-proof.py`.

## Verification

- `python3 scripts/stash-send-chat-control-proof.py`
- `python3 scripts/stash-actions-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies stash send updates both `/state.chatControlActions` and
  `/state.stashActions`.
