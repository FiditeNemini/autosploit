# Checkpoint 310 - Chat Cache Session Field Proof Map

## Goal
Tie each visible chat cache-session field to concrete proof scripts.

## Changes
- Added `/qa/chat-coverage.cacheSessionFieldProofs`.
- Added `cacheSessionFieldProofCount` and `cacheSessionFieldProofParity`.
- Mirrored cache-session field proof count/parity into `/qa/coverage-index.groups.chatAndContext`.
- Extended the broad QA matrix smoke proof to check the new chat cache-session field proof count/parity.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/chat-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red chat coverage proof failed because `/qa/chat-coverage` listed
cache-response method, explicit cache-response inference method, session
boundary mode, new model session behavior, prefix cache, prompt L2 disk, paged
cache, block L2 disk, and TurboQuant KV without mapping each field to the proof
scripts that validate it. The green path adds that map and mirrors proof
count/parity through the chat/context coverage-index group.
