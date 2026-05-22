# Checkpoint 316 - Result Parser Tool Sets Aggregate

## Goal

Make the top-level coverage index expose the structured parser branches and
raw-only tool preservation set covered by the parser fixture proof.

## Changes

- Added `resultParserStructuredTools` to `/qa/coverage-index.groups.toolsAndParsers`.
- Added `resultParserRawOnlyTools` to `/qa/coverage-index.groups.toolsAndParsers`.
- Lifted the parser tool sets into shared AppState constants so
  `/qa/result-parser-coverage` and `/qa/coverage-index` use the same contract.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py` to assert both aggregate parser sets.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the tools/parsers aggregate exposed
structured/raw counts but not the parser branch sets behind those counts. The
green path now makes parser breadth and raw-only preservation visible from the
top-level QA index without requiring the parser fixture seed route first.
