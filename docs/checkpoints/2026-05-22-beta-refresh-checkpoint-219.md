# Checkpoint 219 - Context Coverage State Keys

## Goal

Make `/qa/context-coverage` expose the AppState and message audit keys behind
dynamic catalogue, request audit, embeddings, stash retrieval, semantic CVE, and
new-context cache preservation proofs.

## Changes

- Strengthened `scripts/context-coverage-proof.py` to require context
  `stateKeys`.
- Updated `GET /qa/context-coverage` with the state/message audit surfaces used
  by context proof scripts.
- Strengthened `scripts/app-qa-matrix-smoke-proof.py` so the top-level matrix
  catches missing context state-key accounting.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/context-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/context-coverage` listed routes, contracts,
and proofs but did not expose the state/message audit keys those proofs validate.
The green path adds that state-key contract.
