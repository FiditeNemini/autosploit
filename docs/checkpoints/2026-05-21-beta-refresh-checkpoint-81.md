# Checkpoint 81 - Dynamic Tool Schema Catalogue

## Scope

- Remove the remaining all-at-once tool schema injection path.
- Keep model-callable context/CVE/shell callbacks visible while selecting
  external tool schemas by current prompt and active tab.
- Prove the live request body stays bounded without returning to
  small/medium/large model profiles.

## Changes

- `ToolDefinitions.forModel(...)` now accepts `query`, `activeTab`, `maxTools`,
  and `includeUnavailable`.
- Built-in `search_context`, `search_cve`, `lookup_cve`, and `run_shell`
  schemas are always visible.
- External tools are ranked by tab lane plus query-term matches and capped at
  12 schemas by default.
- `ChatService.streamCompletion()` now passes the latest user prompt and active
  tab into the selector before sending `/v1/chat/completions`.
- The QA server exposes `/qa/tool-catalog` for deterministic proof of the
  selector, including unavailable tools so taxonomy can be tested even on a
  machine without every binary installed.
- `scripts/live-turn-harness.py` now fails if a web-tab request carries
  unrelated OSINT/exploit schemas.

## Proof

- `python3 scripts/tool-catalog-proof.py`
- `python3 scripts/live-turn-harness.py`
- `swift build --package-path ExploitBot`

The proof confirms:

- web-lane prompts include catalogue/CVE callbacks plus relevant web tools such
  as `nuclei` and `sqlmap`, but not `sherlock` or `sliver`;
- OSINT prompts include `sherlock` and `holehe`, but not `sqlmap` or
  `metasploit`;
- live chat requests remain bounded to 12 schemas or fewer and preserve the
  context catalogue, agentic tool loop, metrics, stop behavior, and new-context
  cache-preservation proof.

## Remaining

- Persist per-turn retrieval/tool-schema decisions for audit.
- Add visible "context used" and "tools exposed" inspection in the chat/tool
  panel.
