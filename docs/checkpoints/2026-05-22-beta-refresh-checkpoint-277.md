# Checkpoint 277 - Coverage Index Chat Cache Badges

## Goal
Carry the chat header cache-session badge contract into `/qa/coverage-index.groups.chatAndContext`.

## Changes
- Updated `scripts/coverage-index-proof.py` to require the chat/context group to mirror `/qa/chat-coverage` cache badge fields.
- Added `headerCacheBadges`, `cacheSessionIndicator`, and `newContextSessionBoundary` to the coverage-index chat/context group.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/chat-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red coverage-index proof failed because the chat/context group only exposed state-key count. The green path mirrors the visible chat cache-session badge contract from `/qa/chat-coverage`.
