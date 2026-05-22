# Checkpoint 187 - Tool Flow Coverage Endpoint

## Goal

Expose the model-tool execution/result pipeline through a machine-readable QA
route so registry, parser routing, representative fanout, and context-catalog
coverage can be audited together.

## Changes

- Added `scripts/tool-flow-coverage-proof.py`.
- Added `GET /qa/tool-flow-coverage`, returning:
  - live tool and callback counts from `ToolDefinitions.coverageReport()`
  - underlying QA coverage routes
  - representative tool families
  - registry/parser/fanout/context-catalog contract flags
  - proof scripts for the tool-flow pipeline
- Extended `scripts/app-qa-matrix-smoke-proof.py` to require the new route and
  validate its registry counters.
- Updated app flow and system review docs with the new audit route.

## Proof

```bash
python3 scripts/tool-flow-coverage-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
python3 scripts/tool-registry-coverage-proof.py
```

## Notes

The red proof failed because `GET /qa/tool-flow-coverage` did not exist. The
green proof verifies the aggregate route agrees with `/qa/tool-coverage` on live
tool counts and names the parser, fanout, and context-catalog proof gates.
