# Beta Refresh Checkpoint 166

## Scope

- Make the Python `/v1/responses` API honor `store=true` and
  `previous_response_id` for model-session continuation.
- Preserve the app's "new context window" behavior: a fresh session is started
  by omitting `previous_response_id`, while the existing engine process and
  prefix/L2 cache topology stay available for repeated long context.

## Changes

- Added a bounded in-process Responses session store in
  `ExploitBotEngine/vmlx_engine/server.py`.
- Stored Responses turns are normalized into chat messages and replayed before
  the current request when `previous_response_id` is supplied.
- Reasoning output items are not replayed into the prompt; assistant text and
  function-call outputs are carried forward for normal context/tool loops.
- Unknown `previous_response_id` now returns a 404 instead of silently starting
  a wrong context.

## Proof

- Red proof first:
  `ExploitBotEngine/.venv/bin/python -m pytest ExploitBotEngine/testsuite/test_responses_session_store.py -q`
  failed because the response-session helpers did not exist.
- Green proof:
  `.venv/bin/python -m pytest testsuite/test_responses_session_store.py -q`
  from `ExploitBotEngine` passed.
- Regression proof:
  `.venv/bin/python -m pytest testsuite/test_server_cache_defaults.py testsuite/test_launch_model_defaults.py -q`
  from `ExploitBotEngine` passed.
- Full engine proof:
  `.venv/bin/python -m pytest testsuite -q`
  from `ExploitBotEngine` passed with `64 passed`.
- App build proof:
  `swift build --package-path ExploitBot` passed.
- Live context-window proof:
  `python3 scripts/context-window-cache-proof.py --output docs/live-proofs/checkpoint-166-context-window-cache-proof.json`
  passed and wrote the proof artifact.
