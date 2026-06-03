# Beta Refresh Checkpoint 464 - Supply-Chain Visual Family Parity

Date: 2026-06-03

## Goal

Close the remaining visual tab proof-family parity gap by making the supply-chain/CVE UI visual proof visible from `/qa/visual-coverage`.

## Changes

- Strengthened `scripts/visual-coverage-proof.py` to require the `supplyChain` visual tab family.
- Added `supplyChain` to `visualTabProofFamilies` with `visual-cve-settings-status-proof.py`.
- Updated `README.md` to document per-tab visual proof-family parity.

## Proof

Red path:

- `python3 scripts/visual-coverage-proof.py`
- Expected failure before route wiring: `visual tab family keys mismatch`.

Green path:

- `python3 scripts/visual-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`

## Remaining

This closes the visual tab-family parity gap. It does not close the known Qwen multimodal runtime promotion gap or replace live Qwen/MiniMax model load/chat proof.
