# Checkpoint 51 - Dynamic Context Catalogue

## Summary

Added the first app-side dynamic context catalogue. Chat turns now build a
prompt-aware context packet from current session artifacts instead of always
injecting one fixed ResultsStore summary.

## Changes

- Added `ContextCatalogService`.
- Added `ContextCatalogConfig` and `ContextCVEMode`.
- Changed `ChatService.onContextUpdate` to accept the latest user prompt and
  return an async ranked context packet.
- Wired main chat through `AppState.wireContextCatalog(...)`.
- Wired newly deployed agents through the same catalogue service.
- Added local settings persistence for:
  - dynamic context enabled
  - max injected snippets
  - include assets
  - include findings
  - include recent tool output
  - include stash
  - CVE assist mode
- Added a Settings `CONTEXT CATALOG` section with toggles and CVE assist mode
  selector.
- Updated the app-flow inventory to distinguish implemented catalogue behavior
  from the remaining model-callable retrieval-tool lane.

## Behavior

The catalogue indexes:

- parsed ports, subdomains, web hosts, network hosts, and OSINT rows
- parsed vulnerabilities and CVE IDs
- recent raw tool output
- stash items
- current or semantically ranked CVE results

The injected packet includes counts and provenance labels such as `asset.port`,
`finding`, `tool.output`, `stash.raw`, and `cve`. Semantic CVE mode calls the
local CVE embedding path when available and falls back through `CVEService`
behavior when embeddings are absent.

## Remaining Work

- Add a model-callable catalogue search tool so the model can request more
  context after reading the compact packet.
- Store retrieval decisions with the chat turn for later inspection.
- Add a visible "context used" panel in chat.
- Add durable embeddings for non-CVE catalogue items.
- Add per-tab tool progress/status indicators tied to `onToolStart` and
  `onToolComplete`.

## Verification

Run after this checkpoint:

```bash
swift build --package-path ExploitBot
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q
git diff --check
rg -n "onContextUpdate|ContextCatalog|context.catalog" ExploitBot/Sources/ExploitBot -g '*.swift'
```

Visual QA should confirm the Settings Context Catalog section is visible and
that its controls fit within the current squared dark settings surface.
