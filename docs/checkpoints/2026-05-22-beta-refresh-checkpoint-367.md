# Checkpoint 367 - Context Proof File Parity

## Goal

Make `/qa/context-coverage` expose proof-file parity and mirror that flag
through `/qa/coverage-index.groups.chatAndContext`.

## Changes

- Added `proofFileParity` to `/qa/context-coverage`.
- Added `contextProofFileParity` to the chat/context coverage-index aggregate.
- Extended `scripts/context-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/context-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/context-coverage` listed proof files for
bounded catalogue injection, search_context, retrieval sources, delivery modes,
stash retrieval, and context-window cache preservation without a route-owned
machine-readable parity flag proving those files exist.
