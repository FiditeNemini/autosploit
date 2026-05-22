# Checkpoint 279 - Chat Cache Badge Parity

## Goal
Expose a parity flag proving the visible chat cache-session badge list and badge count agree.

## Changes
- Updated `scripts/chat-coverage-proof.py` to require `headerCacheBadgeParity`.
- Updated `scripts/coverage-index-proof.py` to require the coverage-index chat/context group to mirror `headerCacheBadgeParity`.
- Added `headerCacheBadgeParity` to `/qa/chat-coverage` and `/qa/coverage-index.groups.chatAndContext`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/chat-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red chat coverage proof failed because badge list and count were exposed without an explicit parity flag. The green path makes the visible cache-session badge contract self-checking.
