# Checkpoint 144 - Chat Header Controls

## Scope

- Make chat header reasoning, request-context inspector, and new-context
  controls observable through AppState instead of direct `ChatService` mutation
  from the view.

## Changes

- Added `ChatControlActionState` and exposed it as
  `/state.chatControlActions`.
- Added deterministic QA routes `/qa/seed-chat-control-actions` and
  `/qa/chat-control-action`.
- Routed visible ChatPanel reasoning toggle, request-context inspector toggle,
  and new-context confirmation through AppState callbacks.
- `AppState.startNewContextWindow()` now also closes the request-context
  inspector and records visible cache-preserving control telemetry.
- Added `scripts/chat-control-actions-proof.py`.

## Verification

- `python3 scripts/chat-control-actions-proof.py`
- `python3 scripts/context-window-cache-proof.py`
- `python3 scripts/live-turn-harness.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies reasoning state, context inspector visibility, context
  generation, message clearing, visible activity, and preservation of the
  `prefix-cache-l2-turboquant` context-window response path.
