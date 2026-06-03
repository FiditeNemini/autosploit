# Beta Refresh Checkpoint 472 - Security Abuse Boundary Matrix

Date: 2026-06-03

## Goal

Make the pentest/supply-chain abuse boundary auditable from the app instead of
leaving it as scattered shell, authorization, CVE, prompt-boundary, and audit
checks.

## Changes

- Added `GET /qa/security-abuse-boundary-matrix`.
- Added `scripts/security-abuse-boundary-matrix-proof.py`.
- The route ties together:
  - authorized pentest tooling coverage;
  - destructive `run_shell` pattern blocklist behavior;
  - manual, copilot, and autopilot authorization modes;
  - supply-chain/CVE include-only import guardrails;
  - bounded prompt/context policy;
  - audit-ledger and live tool-status logging surfaces.
- Mirrored the route through `/state.qaCoverage.stateRoutes` and
  `/qa/coverage-index.toolsAndParsers`.
- Updated the README beta lane and runtime proof command list.

## Proof

Red path:

- `python3 scripts/security-abuse-boundary-matrix-proof.py`
- Expected failure before route wiring:
  `security boundary matrix failed: {'error': 'unknown: GET /qa/security-abuse-boundary-matrix'}`

Green path:

- `python3 scripts/security-abuse-boundary-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/beta-readiness-coverage-proof.py`
- `swift build --package-path ExploitBot -c debug`
- `git diff --check`

## Remaining

This checkpoint makes the abuse-boundary contract app-visible and proof-backed.
It does not replace a manual adversarial review of logging, command safety, or
operator misuse cases before wider distribution.
