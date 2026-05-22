# Checkpoint 301 - Context Delivery Proof Map

## Goal
Tie each dynamic-context delivery mode to concrete proof scripts.

## Changes
- Added `/qa/context-coverage.contextDeliveryModeProofs`.
- Added `contextDeliveryModeProofCount` and `contextDeliveryModeProofParity`.
- Mirrored delivery-mode proof count/parity into
  `/qa/coverage-index.groups.chatAndContext`.
- Added `persistence-proof.py` to the context coverage proof set because
  persisted turn audit depends on durable message storage.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/context-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`

## Notes
The red context coverage proof failed because `/qa/context-coverage` exposed
delivery modes but did not map automatic bounded injection, on-demand
`search_context`, persisted turn audit, durable embedding index, and active-scope
stash retrieval to the scripts proving them. The green path adds that map and
mirrors proof count/parity through the coverage index.
