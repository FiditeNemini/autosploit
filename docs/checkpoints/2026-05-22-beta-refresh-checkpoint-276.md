# Checkpoint 276 - Chat Coverage Header Cache Badges

## Goal
Promote the chat header cache-session badges from a visual-only proof into the aggregate `/qa/chat-coverage` contract and broad app QA matrix.

## Changes
- Updated `scripts/chat-coverage-proof.py` to require `headerCacheBadges`, `cacheSessionIndicator`, and `newContextSessionBoundary`.
- Updated `scripts/app-qa-matrix-smoke-proof.py` to check the same chat coverage badge contract.
- Added the badge fields and `visibleCacheSessionBadges` contract to `/qa/chat-coverage`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/chat-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/visual-chat-proof.py`
- `python3 scripts/context-window-cache-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red chat coverage proof failed because `/qa/chat-coverage` did not expose the cache-session header badge contract. The green path makes that visible behavior part of the broad machine-readable QA surface.
