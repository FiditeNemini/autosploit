# Checkpoint 382 - Release Readiness QA Surface

## Goal

Make beta release/package readiness visible in the same QA ledger and coverage
index used for app tabs, tools, runtime, context, and visual proof surfaces.

## Changes

- Added `/qa/release-readiness`.
- Added a `release` proof-ledger category and placed
  `release-readiness-proof.py` under that category.
- Added `/qa/coverage-index.groups.releaseReadiness`.
- Exposed release manifest field parity, app/DMG/script/doc artifact presence,
  release proof-file parity, Team ID, hardened runtime flag, notarization state,
  hash lengths, bundled resource flags, and the explicit notary-profile gate.
- Updated audit and coverage proof expectations so release readiness is no
  longer hidden under the generic proof category.
- Updated the system review with the release/package QA surface.

## Proof

- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`

## Notes

The red proof failed because `release-readiness-proof.py` was categorized as
`other` and no `/qa/release-readiness` route or coverage-index release group
existed.
