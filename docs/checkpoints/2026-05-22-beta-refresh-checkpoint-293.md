# Checkpoint 293 - Context Delivery Mode Contract

## Goal
Make the dynamic context anti-flooding strategy explicit from aggregate QA
coverage.

## Changes
- Added `/qa/context-coverage.contextDeliveryModes`.
- Added `contextDeliveryModeCount` and `contextDeliveryModeParity`.
- Mirrored those fields into `/qa/coverage-index.groups.chatAndContext`.
- Strengthened the focused context proof, coverage-index proof, and broad app
  QA matrix.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/context-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes
The red context coverage proof failed because the aggregate exposed retrieval
sources and snippet caps but not the distinct delivery modes that prevent
routine prompt flooding. The green path names automatic bounded injection,
on-demand `search_context`, persisted turn audit, durable embeddings, and
active-scope stash retrieval with list/count/parity checks.
