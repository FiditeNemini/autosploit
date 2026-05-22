# Checkpoint 363 - Tool Flow Proof File Parity

## Goal

Make `/qa/tool-flow-coverage` own proof-file parity instead of leaving the
top-level coverage index to recompute it.

## Changes

- Added `proofFileParity` to `/qa/tool-flow-coverage`.
- Changed `/qa/coverage-index.groups.toolsAndParsers.toolFlowProofFileParity`
  to mirror the tool-flow route-owned flag.
- Extended `scripts/tool-flow-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/tool-flow-coverage` listed proof files without
a route-owned machine-readable parity flag proving those files exist. The green
path makes the tool-flow route the source of truth and keeps the coverage index
as a mirror.
