# Checkpoint 366 - Chat Proof File Parity

## Goal

Make `/qa/chat-coverage` expose proof-file parity and mirror that flag through
`/qa/coverage-index.groups.chatAndContext`.

## Changes

- Added `proofFileParity` to `/qa/chat-coverage`.
- Added `chatProofFileParity` to the chat/context coverage-index aggregate.
- Extended `scripts/chat-coverage-proof.py`, `scripts/coverage-index-proof.py`,
  and `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/chat-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/chat-coverage` listed proof files for chat,
reasoning, controls, context, and cache-session behavior without a route-owned
machine-readable parity flag proving those files exist. The green path makes
chat proof-file existence auditable from the route and mirrored by the top-level
coverage index.
