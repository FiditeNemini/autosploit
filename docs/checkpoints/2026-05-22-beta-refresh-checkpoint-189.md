# Checkpoint 189 - Context Coverage Endpoint

## Goal

Expose the dynamic context/catalog/embedding/stash proof contract through a
machine-readable QA route so bounded prompt context and on-demand retrieval are
auditable together.

## Changes

- Added `scripts/context-coverage-proof.py`.
- Added `GET /qa/context-coverage`, returning:
  - `search_context` as the on-demand catalogue tool name
  - the default max-snippet setting, fixed automatic injection cap, current
    configured max snippets, and current effective injection limit
  - context seed/query QA routes for packet, scope, embeddings, stash retrieval,
    and semantic CVE fixtures
  - contract flags for bounded catalogue injection, request audit persistence,
    parsed result-to-context routing, agent `search_context`, durable embedding
    audit, targeted stash retrieval, and new-context cache preservation
  - proof scripts covering each contract
- Extended `scripts/app-qa-matrix-smoke-proof.py` to require the new route.
- Updated app flow and system review docs with the context coverage route.

## Proof

```bash
python3 scripts/context-coverage-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
```

## Notes

The red proof failed because `GET /qa/context-coverage` did not exist. During
green verification, persisted settings showed that the current context snippet
limit can be lower than the fixed automatic cap, so the endpoint now exposes
both the cap and the current effective limit.
