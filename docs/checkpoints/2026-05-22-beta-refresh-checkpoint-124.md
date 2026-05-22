# Checkpoint 124 - app QA matrix smoke proof

## Scope

- Turn the remaining informal no-model QA matrix smoke lane into a repeatable
  proof script.
- Make the app expose the QA coverage contract through `/state`.

## Changes

- Added `scripts/app-qa-matrix-smoke-proof.py`.
  - Statically rejects removed model-profile symbols:
    `ModelProfile`, `modelProfile`, `maxToolCount`, `modelProfileHint`, and
    `curatedModels`.
  - Verifies required context hooks are still present:
    `onContextUpdate`, `search_context`, `lastContextSummary`,
    `lastToolSchemaNames`, and `context.catalog.maxSnippets`.
  - Launches the app TestServer and smokes `/state`, `/messages`, and
    `/results`.
  - Verifies `/state.qaCoverage` advertises the same profile-removal,
    context-hook, and route-smoke contract.
- Added `/state.qaCoverage` with:
  - `staticProfilesRemoved`;
  - `testServerSmoke`;
  - required context hook names;
  - smoke-tested state routes.
- Updated the system review and flow inventory to list the new proof gate.

## Verification

- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

- This is a no-model QA coverage gate. It does not replace the functional
  context-catalog, tool-loop, parser, or real-model cache proofs.
