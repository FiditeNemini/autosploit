# Checkpoint 341 - Chat Context Aggregate Detail

## Goal

Make `/qa/coverage-index.groups.chatAndContext` preserve detailed chat and
context coverage from `/qa/chat-coverage` and `/qa/context-coverage`.

## Changes

- Added chat route list/count, contract map/count, proof list/count, and
  state-key list/count.
- Added context search tool name, automatic context cap, and current injected
  context limit.
- Added context route list/count, contract map/count, proof list/count, and
  state-key list/count.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because the aggregate carried cache badge/session and
retrieval/delivery proof maps, but not the route, contract, proof-list, state-key
and context-cap detail from the detailed chat/context endpoints. The green path
keeps chat streaming controls, request context, dynamic catalogue retrieval, and
cache-session behavior auditable from the top-level QA index.
