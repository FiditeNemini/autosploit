# Checkpoint 220 - Tool Flow State Keys

## Goal

Make `/qa/tool-flow-coverage` expose the message and AppState keys behind model
tool-call fanout proofs.

## Changes

- Strengthened `scripts/tool-flow-coverage-proof.py` to require tool-flow
  `stateKeys`.
- Updated `GET /qa/tool-flow-coverage` with message tool-card, tab activity,
  activity-feed, results, and context-catalog state surfaces.
- Strengthened `scripts/app-qa-matrix-smoke-proof.py` so the top-level matrix
  catches missing tool-flow state-key accounting.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/tool-flow-coverage` listed routes, contracts,
families, and proofs but did not expose the message/AppState surfaces those
proofs validate. The green path adds that state-key contract.
