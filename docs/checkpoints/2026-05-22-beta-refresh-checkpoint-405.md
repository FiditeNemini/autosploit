# Beta Refresh Checkpoint 405

## Goal

Make CVE taxonomy source feeds, software families, vulnerability classes, risk
signals, and evidence-flow steps expose list/count parity from the source route
and chat/context aggregate.

## Changes

- Added `sourceFeedParity`, `softwareFamilyParity`,
  `vulnerabilityClassParity`, `riskSignalParity`, and `evidenceFlowParity` to
  `/qa/cve-taxonomy-coverage`.
- Mirrored the same parity flags through
  `/qa/coverage-index.groups.chatAndContext`.
- Strengthened CVE taxonomy, coverage-index, and broad app QA matrix proofs so
  modern vuln/software taxonomy breadth cannot silently drift from route-owned
  lists/counts.
- Updated the system review and flow inventory with the CVE taxonomy parity
  contract.

## Proof

- `python3 scripts/cve-taxonomy-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red CVE taxonomy proof failed because `/qa/cve-taxonomy-coverage` exposed
source/software/vulnerability/risk/evidence lists and counts without parity
flags. The green path makes broad CVE, top vuln, software-family, risk, and
evidence-flow coverage measurable from both the source route and chat/context
aggregate.
