# Beta Refresh Checkpoint 447

## Goal

Add a CVE taxonomy matrix so every source feed, software family, vulnerability
class, risk signal, and evidence-flow stage has row-level proof and route
ownership.

## Changes

- Added `scripts/cve-taxonomy-matrix-proof.py`.
- Added `/qa/cve-taxonomy-matrix`.
- Added `/qa/cve-taxonomy-matrix` to `/state.qaCoverage.stateRoutes`.
- Added source-feed, software-family, vulnerability-class, risk-signal, and
  evidence-flow rows linked to `/qa/cve-taxonomy-coverage`,
  `/qa/context-flow-matrix`, `/qa/evidence-lifecycle-flow-matrix`, and
  `/qa/coverage-index`.
- Mirrored `cveTaxonomyMatrixCount`,
  `cveTaxonomyMatrixProofFileParity`,
  `cveTaxonomyMatrixRowProofFileParity`, and
  `cveTaxonomyMatrixEvidenceFlowCount` into
  `/qa/coverage-index.groups.chatAndContext`.
- Updated coverage-index and app matrix proofs to require the new CVE taxonomy
  matrix route and mirrors.
- Updated the system review and flow inventory docs with the CVE taxonomy
  matrix contract.

## Proof

- `python3 scripts/cve-taxonomy-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/cve-taxonomy-matrix` did not exist. The green
path keeps CVE source feeds, taxonomy breadth, risk ranking signals, and
evidence-flow stages tied to proof-owned context and evidence lifecycle routes.
