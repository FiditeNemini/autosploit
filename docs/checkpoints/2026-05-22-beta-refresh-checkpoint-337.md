# Checkpoint 337 - Result Parser Artifact Aggregate

## Goal

Make `/qa/coverage-index.groups.toolsAndParsers` preserve representative
parsed artifact lists from seeded `/qa/result-parser-coverage`.

## Changes

- Added `resultParserSubdomains` and `resultParserWebUrls`.
- Added `resultParserVulnSources` and `resultParserVulnTitles`.
- Added `resultParserPorts`, `resultParserNetworkHosts`, and
  `resultParserOsintPlatforms`.
- Added `resultParserPostLabels` and `resultParserRawTools`.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red coverage-index proof failed because the tools/parsers aggregate exposed
seeded result-parser counts, parsed tools, raw-only tools, and failures, but not
the representative parsed artifact lists. The green path keeps concrete parser
output artifacts visible from the top-level QA index after seeding the parser
fixture.
