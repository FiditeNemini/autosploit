# Checkpoint 208 - Tool Flow Fixture Seed Route Coverage

## Goal

Make `/qa/tool-flow-coverage` expose the fixture seed routes behind parser
routing and tool-family fanout proofs.

## Changes

- Strengthened `scripts/tool-flow-coverage-proof.py` to require
  `/qa/seed-result-parser-fixture` and `/qa/seed-tool-family-fanout-fixture`.
- Updated `GET /qa/tool-flow-coverage` with those seed routes.
- Updated docs with parser/fanout fixture seed route coverage.

## Proof

- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/parser-fanout-aggregate-proof.py`
- `python3 scripts/result-parser-routing-proof.py`
- `python3 scripts/tool-family-fanout-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/tool-flow-coverage` named parser and fanout
coverage endpoints but omitted the fixture seed routes required to exercise
those contracts. The green path keeps the registry/parser/fanout contract
unchanged while exposing the setup routes used by the proof suite.
