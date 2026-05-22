# Checkpoint 311 - Chat Header Cache Badge Proof Map

## Goal

Tie each visible chat header cache badge to concrete proof scripts.

## Changes

- Added `/qa/chat-coverage.headerCacheBadgeProofs`.
- Added `headerCacheBadgeProofCount` and `headerCacheBadgeProofParity`.
- Mirrored header cache badge proof count/parity into `/qa/coverage-index.groups.chatAndContext`.
- Extended the broad QA matrix smoke proof to check the new chat header cache badge proof count/parity.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/chat-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red chat coverage proof failed because `/qa/chat-coverage` listed `ctx`,
`cache preserved`, `prefix/l2/tq`, and `new ctx keeps cache` header badges
without mapping each visible badge to the proof scripts that validate it. The
green path adds that map and mirrors proof count/parity through the chat/context
coverage-index group.
