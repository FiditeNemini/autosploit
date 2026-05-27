# Beta Refresh Checkpoint 429

## Goal

Make the Qwen multimodal runtime blocker source-owned so dormant MLLM
scaffolding cannot be mistaken for a promotable Qwen VL runtime path.

## Changes

- Added `scripts/qwen-multimodal-runtime-blocker-proof.py`.
- Verified `ExploitBotEngine/vmlx_engine/models/mllm.py` remains an explicit
  `MLXMultimodalLM` stub that raises `NotImplementedError`.
- Verified `SimpleEngine` still routes force/autodetected MLLM loads through
  that stub.
- Added `qwen-multimodal-runtime-blocker-proof.py` to the
  `/qa/gap-ledger.gapContracts.qwenMultimodalRuntime.proofs` contract.
- Updated `scripts/gap-ledger-proof.py` to require the new blocker proof.
- Updated the system review with the stubbed MLLM loader blocker.

## Proof

- `python3 scripts/qwen-multimodal-runtime-blocker-proof.py`
- `python3 scripts/gap-ledger-proof.py`
- `python3 scripts/qwen-multimodal-start-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because the Qwen multimodal gap did not yet name the
runtime-blocker proof. The green path keeps promotion blocked until the
`MLXMultimodalLM` stub is replaced by a real loader and the three live
promotion proofs exist and pass.
