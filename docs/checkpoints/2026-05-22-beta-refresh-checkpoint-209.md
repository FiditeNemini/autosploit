# Checkpoint 209 - Tool Flow Proof Count Metadata

## Goal

Make `/qa/tool-flow-coverage` expose proof-count metadata alongside registry,
parser, fanout, and fixture route coverage.

## Changes

- Strengthened `scripts/tool-flow-coverage-proof.py` to require
  `proofCount`.
- Updated `GET /qa/tool-flow-coverage` with proof-count metadata.
- Updated docs with tool-flow proof-count coverage.

## Proof

- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/tool-flow-coverage` listed the focused proof
scripts but did not expose a direct proof count. The green path preserves the
registry/parser/fanout contract while making tool-flow proof breadth
machine-checkable.
