# Checkpoint 59 - Lean Context Injection

## Summary

Reduced automatic context injection so the model does not get flooded with
notes, embeddings, and stale findings on every turn. The default path now sends
only a small ranked packet and explicitly tells the model to use
`search_context` for deeper targeted retrieval.

## Changes

- Changed `ContextCatalogConfig.maxSnippets` default from 8 to 4.
- Capped automatic `onContextUpdate` injection to 4 snippets.
- Kept the `search_context` tool able to return up to 8 targeted snippets.
- Added explicit catalogue guidance: use `search_context` for more notes,
  assets, findings, tool output, or CVEs instead of requesting all context in
  the prompt.
- Clamped persisted Context settings to 1-8 snippets.
- Updated Settings default/placeholder for Max Snippets to 4.
- Updated the QA seed finding title so bounded snippets prove the exact Apache
  2.4.49 version and CVE path within the test-server preview.

## Verification

The live-turn harness now proves:

- the automatic dynamic context packet is capped at 4 snippets or fewer;
- the automatic packet includes guidance to use `search_context`;
- `search_context` still returns targeted Apache 2.4.49 and CVE-2021-41773
  context when requested.

```bash
python3 scripts/live-turn-harness.py
swift build --package-path ExploitBot
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q
```
