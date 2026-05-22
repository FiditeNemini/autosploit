# Checkpoint 149 - Chat Turn Controls

## Scope

- Route visible chat send, stop, approve, reject, and clear/new-context actions
  through AppState and prove the action telemetry.

## Changes

- Added `AppState` wrappers for chat send, generation stop, pending tool-call
  approval, and pending tool-call rejection.
- Routed `/send`, `/stop`, `/approve`, `/reject`, and `/clear` through the
  AppState chat-control path.
- Routed `ChatPanelView` send, stop, approval, and rejection controls through
  callbacks supplied by `ContentView`.
- Added `scripts/chat-turn-controls-proof.py`.

## Verification

- `python3 scripts/chat-turn-controls-proof.py`
- `python3 scripts/chat-control-actions-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The new proof checks visible turn controls update `/state.chatControlActions`,
  activity feed state, message count after send, and pending approval visibility
  after approve/reject.
