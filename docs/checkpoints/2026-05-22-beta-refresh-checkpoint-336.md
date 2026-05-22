# Checkpoint 336 - Result Parser Aggregate Detail

## Goal

Make `/qa/coverage-index.groups.toolsAndParsers` preserve seeded
`/qa/result-parser-coverage` output details, not only the static structured and
raw-only parser tool sets.

## Changes

- Added fixture seeding to `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py` before reading the aggregate index.
- Added `resultParserCounts`.
- Added `resultParserParsedTools` and `resultParserRawOnlyParsedTools`.
- Added `resultParserFailures` and `resultParserFailureCount`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red coverage-index proof failed because the tools/parsers aggregate carried
the expected structured/raw parser tool sets but not the seeded parser output
counts, parsed structured tools, raw-only preservation list, or failure list.
The green path keeps parser routing evidence visible from the top-level QA
index after the representative parser fixture is seeded.
