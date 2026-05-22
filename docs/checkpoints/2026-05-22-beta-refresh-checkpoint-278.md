# Checkpoint 278 - Chat Cache Badge Count

## Goal
Make the visible chat cache-session badge count explicit in `/qa/chat-coverage` and `/qa/coverage-index.groups.chatAndContext`.

## Changes
- Updated `scripts/chat-coverage-proof.py` to require `headerCacheBadgeCount`.
- Updated `scripts/coverage-index-proof.py` to require the chat/context group to mirror the badge count from `/qa/chat-coverage`.
- Added `headerCacheBadgeCount` to `/qa/chat-coverage` and the coverage-index chat/context group.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/chat-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red chat coverage proof failed because the visible cache-session badge list was exposed without an explicit count. The green path makes badge cardinality machine-checkable.
