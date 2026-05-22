# Beta Refresh Checkpoint 170

## Scope

- Prove the chat "Start New Context" confirmation sheet is AppState-owned and
  visible through `/state`.
- Keep the confirmation path tied to the cache-preserving context reset rather
  than a local-only SwiftUI modal.

## Changes

- Added `isNewContextConfirmVisible` to `AppState`.
- Added AppState actions for open, cancel, and confirm:
  `openNewContextConfirmation`, `cancelNewContextConfirmation`, and
  `confirmNewContextWindow`.
- Wired the chat header trash button and confirmation sheet through AppState.
- Added `/qa/chat-new-context-confirm`.
- Added `/state.qaChatVisual.newContextConfirm`.
- Added `scripts/chat-new-context-confirm-proof.py`.

## Proof

- Red proof first:
  `python3 scripts/chat-new-context-confirm-proof.py` failed because
  `/qa/chat-new-context-confirm` did not exist.
- Green proof:
  `python3 scripts/chat-new-context-confirm-proof.py` passed.
- Cache/session regression:
  `python3 scripts/context-window-cache-proof.py --output docs/live-proofs/checkpoint-170-context-window-cache-proof.json`
  passed.
- Chat control regression:
  `python3 scripts/chat-control-actions-proof.py` passed when run serially.
- Build proof:
  `swift build --package-path ExploitBot` passed.

## Note

- App-owning proof scripts must run serially. A concurrent context-window proof
  can increment context generation while another chat-control proof is between
  assertions.

