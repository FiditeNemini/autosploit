# Checkpoint 291 - Cache Response Session Contract

## Goal
Make the long-context prefix-cache response method and new context-window
session boundary explicit from aggregate QA endpoints.

## Changes
- Added `cacheResponsesInferenceMethod` to `/qa/chat-coverage`.
- Added `newModelSessionBehavior` to `/qa/chat-coverage`.
- Added the same fields to `/qa/runtime-coverage`.
- Mirrored both fields into `/qa/coverage-index.groups.chatAndContext`.
- Mirrored both fields into `/qa/coverage-index.groups.runtimeAndCache`.
- Strengthened chat, runtime, coverage-index, and broad app QA proofs.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/chat-coverage-proof.py`
- `python3 scripts/runtime-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red chat coverage proof failed because `/qa/chat-coverage` exposed the
legacy cache response method and field list but not the explicit
`cacheResponsesInferenceMethod` value. The green path makes the
`prefix-cache-l2-turboquant` inference method and
`new-context-window-preserve-engine-cache-session` boundary visible from both
detailed and aggregate QA routes.
