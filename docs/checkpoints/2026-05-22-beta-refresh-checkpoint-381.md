# Checkpoint 381 - CVE Taxonomy and Tool Flow Proof Parity

## Goal

Add a broad defensive CVE/vulnerability/software taxonomy contract for the
agent, and finish route-owned file parity for tool-flow tab activity and visual
surface proof maps.

## Changes

- Added `/qa/cve-taxonomy-coverage`.
- Added `scripts/cve-taxonomy-coverage-proof.py`.
- Mirrored CVE taxonomy source feeds, software families, vulnerability classes,
  risk signals, evidence flow, agent tools, bounded context contract, and report
  contract through `/qa/coverage-index.groups.chatAndContext`.
- Added `tabActivityStatusProofFileParity` and
  `toolVisualSurfaceProofFileParity` to `/qa/tool-flow-coverage`.
- Mirrored tab activity proof-file parity through tools/parsers and
  tabs/sessions coverage-index groups.
- Mirrored tool visual surface proof-file parity through tools/parsers.
- Extended `scripts/tool-flow-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/cve-taxonomy-coverage-proof.py`
- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red CVE taxonomy proof failed because `/qa/cve-taxonomy-coverage` did not
exist. The red tool-flow proof failed because `/qa/tool-flow-coverage` listed
mapped tab activity proof files without an explicit route-owned file-parity
flag.
