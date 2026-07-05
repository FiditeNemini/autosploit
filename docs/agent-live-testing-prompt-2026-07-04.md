# Agent Live Testing Prompt

Use this prompt for the next Codex/agent pass on ExploitBot. Treat it as an operating checklist, not as proof by itself.

You are working in `/Users/eric/exploitbot`. Use an RLM loop for every claim: read the exact source/proof artifact, live-run the smallest bounded verification that can prove or disprove it, then measure/report current evidence separately from source evidence. Do not claim fixed, working, green, release-ready, or production-ready unless you name current source-trace evidence and live verification evidence.

Primary goal: make ExploitBot semi-functional and displayable within two weeks, with real local Qwen 3.6 27B MXFP8 MTP and Qwen 3.6 35B A3B MXFP8 MTP model paths usable through the app, settings, engine, chat, tools, and autonomous loop.

Current Qwen requirements:

- Verify both target models can receive the intended app prompts and tool schemas.
- Verify `MTP`-named Qwen models prove D3 MTP on the decode/output path, not just metadata presence.
- Verify q4 TurboQuant KV, prefix cache, paged cache, block L2 disk cache, SSM companion disk L2, and hybrid async rederive policy.
- Verify Qwen reasoning-on and reasoning-off chat behavior, TTFT/cached-token metrics where available, and visible warning/final-answer behavior when max-token caps are too low.
- Verify verbose tool usage appears in chat, terminal transcript, results/raw results, and activity/context panes where appropriate.
- Verify real Qwen 27B and 35B drive safe loopback/local tools only unless the user explicitly supplies authorized scope.
- Verify long-context behavior only when no unrelated heavy model/eval process is active; do not stack another Qwen load on top of an active 35B eval without explicit user direction.

Current app requirements:

- Settings must expose engine/model selector, model folder add/scan/select, cache toggles, reasoning toggles, generation controls, and tool settings.
- Toggling settings must change app state and engine config, with proof artifacts or live API/UI evidence.
- Each workflow/tool panel must have either live UI proof or a documented blocker plus app/API/System Events fallback evidence.
- The CVE library must include current CISA/NVD-backed refresh evidence, exact CVE lookup, model-invoked CVE search/lookup, and source attribution in model-visible context.
- Autonomous pentest scenarios must stay safe: loopback/local lab targets, explicit policy blocking for external/high-risk targets, and visible approvals or denials.

Current known blockers:

- Computer Use GUI proof is blocked below ExploitBot: service/socket/schema listing can pass, but actual `list_apps` tool execution fails and first-class `mcp__computer_use` is not exposed in this Codex turn.
- Release distribution is blocked by notarization credentials/flow, even though local app/DMG signature and bundled runtime checks pass.
- Qwen long-context proof remains partial until the unrelated active `osaurus-evals` 35B process exits and `scripts/real-qwen-long-context-smoke-proof.py` can rerun to an `ok=true` artifact.

Minimum verification before any status update:

- `python3 scripts/goal-requirement-audit-proof.py`
- `python3 scripts/qwen-runtime-readiness-proof.py`
- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python3 -m pytest ExploitBotEngine/testsuite/test_qwen_runtime_readiness_contracts.py ExploitBotEngine/testsuite/test_qwen_d3_mtp_output_contracts.py ExploitBotEngine/testsuite/test_goal_requirement_audit_contracts.py -q`
- `jq '{ok,coreStatus,overallStatus,generatedAt,streaming:.streaming.status,reasoning:.reasoning.status,cveLookup:.cveLookup.status,longContext:.blockingEvidence.longContextStatus}' docs/live-proofs/2026-07-04-qwen-runtime-readiness.json`

Always update `docs/live-validation-2026-07-04.md` and the relevant `docs/live-proofs/*.json` artifacts as the source of current progress, partials, blockers, and todos.
