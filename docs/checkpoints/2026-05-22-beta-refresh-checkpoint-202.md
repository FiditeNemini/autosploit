# Checkpoint 202 - Context Coverage New Context Metadata

## Goal

Make `/qa/context-coverage` explicitly expose the new-context route and proof
count behind dynamic catalogue retrieval and cache-preserving context resets.

## Changes

- Strengthened `scripts/context-coverage-proof.py` to require `/context/new`.
- Strengthened the same proof to require context aggregate `proofCount`.
- Updated `GET /qa/context-coverage` with `/context/new` and proof count.
- Updated docs with the dynamic-context aggregate route coverage.

## Proof

- `python3 scripts/context-coverage-proof.py`
- `python3 scripts/context-catalog-proof.py`
- `python3 scripts/result-context-catalog-proof.py`
- `python3 scripts/agent-search-context-proof.py`
- `python3 scripts/request-audit-proof.py`
- `python3 scripts/context-window-cache-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/context-coverage` claimed
`newContextCachePreservation` but did not list the `/context/new` route. The
green path keeps dynamic context bounded through `search_context` while making
cache-preserving context resets auditable from the aggregate endpoint.
