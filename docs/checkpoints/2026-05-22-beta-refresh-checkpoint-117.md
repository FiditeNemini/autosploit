# Checkpoint 117: Tool Registry Coverage Proof

## Scope

- Prove the model-visible tool registry is not an opaque prompt list.
- Expose a QA endpoint that audits each tool's execution path, tab ownership,
  sample CLI routing, and result parser mode.
- Keep `run_shell` always visible while classifying it as a subprocess-backed
  tool, not an app callback.

## Changes

- Added `scripts/tool-registry-coverage-proof.py`.
- Added QA route `GET /qa/tool-coverage`.
- Added `ToolDefinitions.coverageReport()` with:
  - duplicate tool-name detection;
  - tab ownership checks for non-global tools;
  - sample `buildCliArgs(...)` routing checks;
  - callback-vs-subprocess execution metadata;
  - structured-vs-raw result mode metadata;
  - bounded catalogue limit metadata.
- Updated docs so the tool-registry coverage proof is listed in the repeatable
  QA gates.

## Proof

Command:

```bash
python3 scripts/tool-registry-coverage-proof.py
```

Result:

- The proof first failed because `/qa/tool-coverage` did not exist.
- After wiring the endpoint, it failed once on an over-strict fallback audit
  that treated valid `binary == toolName` CLI mappings as missing routing.
- Final proof passed with:
  - `toolCount=38`;
  - `callbackCount=3`;
  - `boundedCatalogueLimit=12`;
  - all nine app tabs represented;
  - `search_context`, `search_cve`, and `lookup_cve` marked as callbacks;
  - core external tools marked as subprocess-backed;
  - raw-only and structured parser tool modes declared.

## Boundary

This proves the registry metadata, routing surface, and parser-mode declarations
for every exposed tool. It does not prove every external binary is installed or
that every parser handles every real-world output variant; those remain covered
by tool settings status, live-turn harnesses, and parser-specific proofs.
