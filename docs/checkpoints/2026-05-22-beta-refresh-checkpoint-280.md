# Checkpoint 280 - App Matrix Chat Cache Badge Parity

## Goal
Lift the chat cache badge count and parity checks into the broad app QA matrix.

## Changes
- Updated `scripts/app-qa-matrix-smoke-proof.py` to require `headerCacheBadgeCount`.
- Updated `scripts/app-qa-matrix-smoke-proof.py` to require `headerCacheBadgeParity`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/chat-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
This is a verification-hardening slice: the existing `/qa/chat-coverage` endpoint already exposed the badge count and parity, and the broad smoke gate now checks those same fields.
