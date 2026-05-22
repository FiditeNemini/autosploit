# Checkpoint 274 - Explicit New Context Cache Session Contract

## Goal
Make the new-context API contract explicitly distinguish a fresh model context window from destroying the long-context prefix/L2/TurboQuant cache session.

## Changes
- Added `cacheResponsesInferenceMethod`, `sessionBoundaryMode`, and `newModelSessionBehavior` to `/state.contextWindow`.
- Updated `scripts/context-window-cache-proof.py` to require the explicit cache-response inference method and new-context session boundary.
- Updated `scripts/chat-new-context-confirm-proof.py` to verify the visible confirmation path preserves the same contract.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/context-window-cache-proof.py`
- `python3 scripts/chat-new-context-confirm-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red context-window proof failed because `/state.contextWindow` only exposed `cacheResponsesMethod`. The green path now makes the inference method and model context-window boundary machine-readable while preserving the engine cache session.
