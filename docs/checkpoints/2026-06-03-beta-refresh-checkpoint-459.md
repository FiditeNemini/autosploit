# Checkpoint 459 - Objective Flow Requirement Matrix

## Goal

Turn the broad objective runtime checklist into a row-level matrix that names
the exact route, proof, evidence level, contracts, and live artifact coverage for
each requested flow.

## Changes

- Added `scripts/objective-flow-requirement-matrix-proof.py`.
- Added `/qa/objective-flow-requirement-matrix`.
- Mirrored the route through `/state` QA route coverage and the
  `releaseReadiness` group in `/qa/coverage-index`.
- Tightened `scripts/objective-runtime-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py` so the new row-level matrix must stay
  aligned with `/qa/objective-runtime-coverage`.
- Added `runtime-coverage-proof.py` to the hybrid SSM objective row because that
  row routes through `/qa/runtime-coverage`.

## Proof

Red path:

```bash
python3 scripts/objective-flow-requirement-matrix-proof.py
```

Initially failed with:

```text
unknown: GET /qa/objective-flow-requirement-matrix
```

Green path:

```bash
python3 scripts/objective-flow-requirement-matrix-proof.py
```

Passed after the route and matrix were added.

## Remaining

- The matrix preserves `objectiveComplete=false` while the Qwen multimodal
  runtime promotion gap remains open.
