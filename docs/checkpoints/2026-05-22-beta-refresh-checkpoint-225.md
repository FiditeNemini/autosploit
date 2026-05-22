# Checkpoint 225 - Tools Parser Index Counts

## Goal

Make `/qa/coverage-index.groups.toolsAndParsers` expose the registry and
representative fanout breadth proven by the focused tool/parser coverage routes.

## Changes

- Strengthened `scripts/coverage-index-proof.py` to require tool count, callback
  count, representative family fanout count, and state-key count on the
  tools/parsers group.
- Updated `GET /qa/coverage-index` so `toolsAndParsers` rolls up
  `ToolDefinitions.coverageReport()` counts and the tool-family fanout fixture
  count.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/tool-registry-coverage-proof.py`
- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/parser-fanout-aggregate-proof.py`
- `python3 scripts/result-parser-routing-proof.py`
- `python3 scripts/tool-family-fanout-coverage-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because the tools/parsers group only exposed endpoint,
proof, and state-key accounting. The green path keeps the focused registry,
parser-routing, and fanout routes authoritative while making their high-level
breadth visible from the top-level QA index.
