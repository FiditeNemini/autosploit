# Beta Refresh Checkpoint 446

## Goal

Add a parser tool matrix so every structured and raw-only result parser tool has
row-level parser, execution, fanout, and coverage-index ownership.

## Changes

- Added `scripts/parser-tool-matrix-proof.py`.
- Added `/qa/parser-tool-matrix`.
- Added `/qa/parser-tool-matrix` to `/state.qaCoverage.stateRoutes`.
- Added one row per result-parser structured/raw-only tool with parser mode,
  parsed evidence, tool-execution presence, family-fanout membership,
  `/qa/result-parser-coverage`, `/qa/tool-execution-matrix`,
  `/qa/tool-family-fanout-coverage`, and `/qa/coverage-index` linkage.
- Mirrored `parserToolMatrixCount`, `parserToolMatrixParsedParity`,
  `parserToolMatrixToolExecutionParity`, and
  `parserToolMatrixProofFileParity` into
  `/qa/coverage-index.groups.toolsAndParsers`.
- Updated coverage-index and app matrix proofs to require the new parser tool
  matrix route and mirrors.
- Updated the system review and flow inventory docs with the parser tool matrix
  contract.

## Proof

- `python3 scripts/parser-tool-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/parser-tool-matrix` did not exist. The green
path keeps result parser coverage tied to per-tool execution rows,
family-fanout tools, docs, and coverage-index mirrors.
