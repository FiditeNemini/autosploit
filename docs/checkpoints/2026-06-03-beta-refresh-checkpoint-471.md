# Beta Refresh Checkpoint 471 - Context Packet Hard Budget

Date: 2026-06-03

## Goal

Close the direct context-packet prompt budget gap so `/qa/context-packet` cannot
stuff a large imported stash/CVE/context set into the model prompt when a caller
requests an aggressive snippet count.

## Changes

- Added `scripts/context-packet-budget-proof.py`.
- Capped direct context packets to 6,000 characters and 8 selected snippets.
- Reduced rendered context snippet size and added an explicit packet budget
  marker in the generated catalogue.
- Mirrored the packet budget through `/qa/context-budget-compaction` and
  `/qa/coverage-index`.
- Updated the README beta lane with the hard context-packet budget.

## Proof

Red path:

- `python3 scripts/context-packet-budget-proof.py`
- Expected failure before the service cap:
  `context packet exceeded prompt budget: 16541 > 6000`

Green path:

- `python3 scripts/context-packet-budget-proof.py`
- `python3 scripts/context-budget-compaction-proof.py`
- `python3 scripts/context-catalog-proof.py`
- `python3 scripts/stash-retrieval-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/beta-readiness-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot -c debug`
- `./script/package_release.sh --skip-notarize`
- `codesign --verify --verbose=2 release/ExploitBot-beta.dmg`
- `hdiutil verify release/ExploitBot-beta.dmg`
- `git diff --check`

Fresh local package artifact:

- DMG: `release/ExploitBot-beta.dmg`
- SHA256: `dbab053373655a044728a41314ca32f1335c5dd619140b4c1330665e90bc7f36`
- Notarization status: local build only, not submitted

## Remaining

This checkpoint closes the direct context-packet over-budget path. It does not
close the tracked Qwen multimodal runtime promotion, multimodal prefix-cache, or
multimodal context-routing live-proof gaps.
