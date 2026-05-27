# 2026-05-27 Beta Checkpoint

This checkpoint records the current beta lane state after the supply-chain, agent-loop, cache/runtime, release-packaging, and README refresh work.

## Done

- Autonomous agents can run with the full registered tool schema set while normal chat stays tab-ranked and bounded.
- Agent state now exposes current/last tool name, status, preview text, running counts, and status lines for UI surfaces and QA routes.
- System prompt/tool policy is wider for autonomous agents without forcing all tools into every normal chat prompt.
- Supply-chain is a first-class app area with CVE Intel, Secrets, SBOM, and Dependencies subtabs.
- Supply-chain tools include `trufflehog`, `syft`, `grype`, `osv_scanner`, `nuclei`, CVE lookup/search, context search, and shell fallback.
- CVE list import supports pasted CVEs or local files plus include-only filtering.
- Terminal path wiring now derives from installed tool paths and exposes state for proof scripts.
- Settings persistence covers reasoning, parser selections, generation defaults, model path, cache toggles, cache budgets, KV quantization, and KV group size.
- Release packaging bundles the Python engine and vMLX-compatible Python runtime, excludes local venv/tests/pycache, signs app/DMG, and writes a release manifest.
- Engine runtime selection verifies required Python modules before launch and reports candidate-level diagnostics.
- Qwen JANG/JANGTQ and MiniMax proof harnesses exercise real release-app startup, chat completions, TurboQuant q4 KV, prefix cache, paged cache, block L2, and repeat cache hits.
- Qwen hybrid SSM cache handling aligns companion state with paged cache lookup/replay and cross-restart disk cache proofing.
- MiniMax full-KV cache hit replay is patched to re-feed lookup/generation prompt tokens correctly.
- ZAYA1-VL has a real narrow multimodal loader path for the beta visual proof instead of the previous MLLM stub.
- README now states the current done/remaining beta status instead of presenting the app as fully public-beta complete.

## Proof artifacts and commands

- `docs/live-proofs/checkpoint-463-release-app-qwen-cross-restart-cache.json`
- `docs/live-proofs/checkpoint-456-release-app-qwen-jangtq-live.json`
- `docs/live-proofs/checkpoint-459-release-app-minimax-live.json`
- `docs/live-proofs/checkpoint-464-zaya-visual-live.json`
- `docs/live-proofs/checkpoint-470-release-app-qwen-small-live.json`
- `docs/live-proofs/checkpoint-471-release-app-mxfp-live.json`
- `scripts/agent-live-tool-status-proof.py`
- `scripts/agent-loop-coverage-proof.py`
- `scripts/supply-chain-cve-ui-proof.py`
- `scripts/cve-settings-actions-proof.py`
- `scripts/terminal-tool-paths-proof.py`
- `scripts/release-readiness-proof.py`
- `scripts/release-app-live-qwen-proof.py`
- `scripts/release-app-live-minimax-proof.py`
- `scripts/release-app-qwen-cross-restart-cache-proof.py`
- `scripts/zaya-visual-live-proof.py`

## Still needs work

- Notarization and stapling are not complete; signed artifacts remain profile-gated.
- Qwen-specific multimodal/VL runtime promotion remains pending; current visual proof is ZAYA1-VL.
- JANGTQ first-turn exact prompt-following is not fully proven beyond bounded smoke/cache prompts.
- Longer realistic autonomous pentest runs are still needed to prove broad tool-choice quality, not only schema availability and bounded mock loops.
- Final visual QA pass needs to cover all tab buttons, hover/status states, scrolling/streaming polish, settings toggles, terminal behavior, and release-app windows.
- Security review remains required for command execution boundaries, logging exposure, operator authorization cues, and potentially dangerous tool defaults.

## Next best checkpoint

Run the signed app through a compact end-to-end beta rehearsal: create a scoped test operation, launch a small Qwen agent in autopilot, let it use context/CVE/tool calls across recon plus supply-chain, verify streamed UI status and logs live, then package/notarize once the local notary profile is configured.
