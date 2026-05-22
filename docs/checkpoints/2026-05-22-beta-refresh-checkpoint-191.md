# Checkpoint 191 - Visual Coverage Endpoint

## Goal

Expose screenshot-backed UI proof coverage through a machine-readable QA route
so visual app states, tab/tool panels, chat controls, settings, cache status,
OSINT artifacts, reports, and unsupported-model warnings can be audited
together.

## Changes

- Added `scripts/visual-coverage-proof.py`.
- Added `GET /qa/visual-coverage`, returning:
  - visual proof contracts for chat tool states, scroll lock, settings
    model/cache state, context inspector, request-audit badges, tab activity,
    subtab lifecycle strips, OSINT screenshots, reports, stash retrieval,
    unsupported model states, post attribution, tool action panels, live cache
    stats, and CVE/tool settings pages
  - visual proof script names covering those contracts
  - checked-in manifest paths under `docs/visual-proofs`
  - manifest and minimum capture counts
- Extended `scripts/app-qa-matrix-smoke-proof.py` to require the new route.
- Updated app flow and system review docs with the visual coverage route.

## Proof

```bash
python3 scripts/visual-coverage-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
```

## Notes

The red proof failed because `GET /qa/visual-coverage` did not exist. The green
proof verifies the route and also reads every required manifest, confirms each
manifest is `ok`, and checks that listed screenshot captures exist with enough
bytes to prove a rendered image artifact.
