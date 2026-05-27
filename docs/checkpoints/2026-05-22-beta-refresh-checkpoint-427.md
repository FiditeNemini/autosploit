# Beta Refresh Checkpoint 427

## Goal

Expose a source-owned proof-suite inventory so proof scripts, live harnesses,
visual checks, runtime checks, route targets, app-launching behavior, and
live-model signals are parsed, grouped, mirrored into coverage, documented, and
tied to proof-file parity.

## Changes

- Added `scripts/proof-suite-inventory-proof.py`.
- Added `/qa/proof-suite-inventory`.
- Added `/qa/proof-suite-inventory` to `/state.qaCoverage.stateRoutes`.
- Added source parsing for `scripts/*-proof.py` plus special harness proofs:
  `live-turn-harness.py`, `verify-live-models.py`, `prove-parser-api.py`,
  `prove-block-l2-cache.py`, and `prove-ssm-rederive-status.py`.
- Added proof-suite grouping for app-state inventory, agent/chat,
  context/evidence, runtime/cache, settings/visuals, tools/parsers,
  tabs/sessions, release readiness, visual proofs, live-model proofs, and
  support/data.
- Added route-target extraction, app-launch detection, visual-capture
  detection, live-model detection, function/class counts, parse parity, and
  proof-file parity to the proof-suite payload.
- Mirrored proof-suite file count, group counts, route-target count,
  app-launching proof count, visual proof count, live-model proof count,
  proof-file parity, and parse parity into
  `/qa/coverage-index.groups.appState`.
- Updated coverage-index and app matrix proofs to require the proof-suite
  inventory endpoint and mirror.
- Updated the system review and flow inventory docs with the proof-suite
  inventory contract.

## Proof

- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/proof-suite-inventory` did not exist. The
green path keeps the script corpus as the authority and uses the app QA routes
as the mirror, so new proof files must remain visible by group, route target,
visual/live behavior, and file parity.
