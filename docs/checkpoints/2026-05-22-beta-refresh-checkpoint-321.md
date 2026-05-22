# Checkpoint 321 - Chat Context Proof Map Aggregate

## Goal

Make the top-level coverage index preserve the detailed proof maps for chat
cache badges, cache-session fields, context retrieval sources, and context
delivery modes.

## Changes

- Added `headerCacheBadgeProofs` and `cacheSessionFieldProofs` to
  `/qa/coverage-index.groups.chatAndContext`.
- Added `retrievalSourceProofs` and `contextDeliveryModeProofs` to the same
  aggregate group.
- Extended `scripts/coverage-index-proof.py` to compare those maps against
  `/qa/chat-coverage` and `/qa/context-coverage`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` with the same broad smoke
  checks.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the chat/context aggregate exposed
visible cache badges, cache-session fields, retrieval sources, delivery modes,
and their proof counts/parity without preserving the proof maps themselves. The
green path keeps the prefix/L2/TurboQuant cache-session UI and bounded dynamic
context routes traceable from the aggregate QA index back to the exact proof
scripts.
