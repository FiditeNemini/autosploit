# Checkpoint 379 - Context Proof Map File Parity

## Goal

Make `/qa/context-coverage` expose file parity for retrieval-source and
delivery-mode proof maps, then mirror both flags through the chat/context
coverage-index aggregate.

## Changes

- Added `retrievalSourceProofFileParity` to `/qa/context-coverage`.
- Added `contextDeliveryModeProofFileParity` to `/qa/context-coverage`.
- Mirrored both fields through `/qa/coverage-index.groups.chatAndContext`.
- Extended `scripts/context-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/context-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/context-coverage` listed retrieval-source
proof files without an explicit route-owned file-parity flag for the mapped
proof files.
