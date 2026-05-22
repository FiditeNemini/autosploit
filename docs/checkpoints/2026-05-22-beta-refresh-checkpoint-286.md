# Checkpoint 286 - Chat Cache Session Field Contract

## Goal
Make chat/cache coverage enumerate the exact preserved-session cache fields for the `prefix-cache-l2-turboquant` response path.

## Changes
- Added `/qa/chat-coverage.cacheSessionFields`.
- Added `cacheSessionFieldCount` and `cacheSessionFieldParity`.
- Mirrored the cache-session field list/count/parity into `/qa/coverage-index.groups.chatAndContext`.
- Strengthened `scripts/chat-coverage-proof.py`, `scripts/coverage-index-proof.py`, and `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/chat-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red chat coverage proof failed because the endpoint exposed visible cache badges and the cache response method, but not the exact session/cache field names that prove a new context window preserves prefix cache, prompt L2 disk, paged cache, block L2 disk, and TurboQuant KV behavior.
