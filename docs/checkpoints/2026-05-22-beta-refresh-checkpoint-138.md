# Checkpoint 138 - Chat Copy And Stash Action State

## Scope

- Make Chat panel copy and stash actions observable through AppState and QA
  proof routes.

## Changes

- Added `ChatActionState` and `/state.chatActions`.
- Added deterministic QA routes:
  - `/qa/seed-chat-actions`
  - `/qa/chat-action`
- Routed Chat transcript copy, message copy, tool-output copy, message stash,
  and latest-assistant stash through AppState callbacks.
- Chat stash now uses `recordStashAdd`, so `/state.stashActions` reflects chat
  stash actions instead of bypassing the Stash action surface.
- `recordStashAdd` now stores a content preview in stash action state.
- Added `scripts/chat-actions-proof.py`.

## Verification

- `python3 scripts/chat-actions-proof.py`
- `python3 scripts/stash-actions-proof.py`
- `python3 scripts/activity-feed-actions-proof.py`
- `python3 scripts/visual-chat-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies transcript copy, assistant-message copy, assistant-message
  stash, latest-assistant stash, and Stash state coupling.
