# Checkpoint 190 - Settings Coverage Endpoint

## Goal

Expose Settings page and action coverage through a machine-readable QA route so
the split Settings UI, model/runtime/cache policy, app-only apply path, engine
actions, CVE/tools/logs panels, agent controls, and visual proof gates can be
audited together.

## Changes

- Added `scripts/settings-coverage-proof.py`.
- Added `GET /qa/settings-coverage`, returning:
  - all Settings categories in sidebar order with page-section metadata
  - supported runtime families (`qwen`, `minimax`)
  - `prefix-cache-l2-turboquant` cache-response method
  - Settings seed/action QA routes for category switching, app-only apply,
    engine cache metrics, CVE actions, tool install actions, inference log
    actions, and agent settings
  - contract flags for split pages, app-only apply without engine restart,
    Start/Stop action state, model-folder warnings, parser autodetect, context
    controls, cache topology, agent controls, CVE/tools/log actions, and visual
    Settings proofs
  - proof scripts covering each contract
- Extended `scripts/app-qa-matrix-smoke-proof.py` to require the new route.
- Updated app flow and system review docs with the Settings coverage route.

## Proof

```bash
python3 scripts/settings-coverage-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
```

## Notes

The red proof failed because `GET /qa/settings-coverage` did not exist. The
green proof verifies the route ties the split Settings pages and every existing
Settings action/status proof into one aggregate contract.
