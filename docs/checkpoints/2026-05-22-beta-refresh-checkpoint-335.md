# Checkpoint 335 - Tool Flow Proof List Aggregate

## Goal

Make `/qa/coverage-index.groups.toolsAndParsers` preserve the actual
`/qa/tool-flow-coverage` proof list and verify every named proof file exists.

## Changes

- Added `toolFlowProofs`.
- Added `toolFlowProofFileParity`.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red coverage-index proof failed because the tools/parsers aggregate carried
`toolFlowProofCount` but not the proof names or file-existence parity. The green
path makes the top-level QA index show exactly which scripts prove the
tool/parser loop and whether those script paths exist.
