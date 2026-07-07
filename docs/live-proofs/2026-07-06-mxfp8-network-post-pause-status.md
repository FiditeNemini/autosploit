# 2026-07-06 MXFP8 Network/Post Pause Status

Status: PARTIAL / paused by user request. No PASS claim.

## What was running

- Script: `scripts/real-qwen-natural-network-credential-post-proof.py`
- Model: `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP`
- Scenario: natural-language network credential/post chain against loopback fixture.
- Required sequence: `nmap -> httpx -> hydra -> netexec -> run_shell -> linpeas`, then final marker/report/cache/MTP checks.

## Preserved live artifacts

- `2026-07-06-real-qwen-natural-network-credential-post-27b-mxfp8-fail-before-linpeas-interrupt.json`
  - `ok=false`, `overall=FAIL`
  - Started `2026-07-06T22:05:39-0700`, finished `2026-07-06T22:12:49-0700`
  - Tool sequence captured from messages: `nmap -> httpx -> hydra -> netexec -> run_shell`
  - Failure boundary: model streamed prose saying Step 6 should run `linpeas`, but no `linpeas` tool call arrived before the 420s proof deadline.

- `2026-07-06-real-qwen-natural-network-credential-post-27b-mxfp8-fail-before-timeout-config.json`
  - `ok=false`, `overall=FAIL`
  - Started `2026-07-06T22:16:54-0700`, finished `2026-07-06T22:24:05-0700`
  - Tool sequence captured from messages: `nmap -> httpx -> hydra`
  - Failure boundary: the proof timeout expired while the app still reported `isStreaming=true`; app stream watchdog had not had enough post-hydra time to fire.

- `2026-07-06-real-qwen-natural-network-credential-post-27b-mxfp8.json`
  - `ok=false`, `overall=FAIL`
  - Started `2026-07-06T22:25:42-0700`, finished `2026-07-06T22:38:52-0700`
  - This file is an interrupted-run marker after user requested pause. It has no `messages`, `state`, or `results`, so it must not be used as a full scenario proof.

## Source changes queued at pause

- `ChatService.swift`: added a narrow `shouldInterruptForLinpeasFallback` semantic interrupt so a slow stream that states linpeas intent after the post-check marker can yield control to the existing bounded `fallbackLinpeasToolCallIfNeeded`.
- `test_chat_service_tool_loop_contracts.py`: covers the semantic linpeas recovery path.
- `real-qwen-natural-network-credential-post-proof.py`: added env-configurable tool/final wait budgets for slow MXFP8 runs.
- `test_natural_app_network_tool_choice_contracts.py`: covers the new timeout env knobs.

## Verification completed before pause

- Focused contract before source edit failed as expected on missing `shouldInterruptForLinpeasFallback`.
- After source edit: `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python -m pytest -q ExploitBotEngine/testsuite/test_chat_service_tool_loop_contracts.py::test_linpeas_fixture_marker_gap_synthesizes_linpeas_tool_for_bounded_network_post_recovery` -> `1 passed`.
- After harness timeout edit: `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python -m pytest -q ExploitBotEngine/testsuite/test_natural_app_network_tool_choice_contracts.py ExploitBotEngine/testsuite/test_chat_service_tool_loop_contracts.py` -> `25 passed`.
- Swift build after ChatService edit: `swift build --package-path ExploitBot -c debug` -> build complete.
- `git diff --check` -> clean.

## Open boundary

27B MXFP8 network/post remains PARTIAL/FAIL. The next validation step is a clean long-budget rerun with no interruption and a PASS requirement for the full sequence, report, cache rows, and `nativeD3MTPForMTPModel`.
