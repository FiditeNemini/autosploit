# Checkpoint 195 - Responses Session Chain Preservation

## Goal

Make Responses API continuation storage preserve the full resolved ancestor
context, so long-context catalogue/session chains do not drop earlier turns when
a child response is stored and then used as `previous_response_id`.

## Changes

- Added a regression test covering parent -> child -> grandchild Responses API
  chaining with `store=true` on the parent and child.
- Fixed `POST /v1/responses` storage to save the resolved message list that was
  actually sent to the engine, instead of only the latest request input.

## Proof

```bash
cd ExploitBotEngine && uv run pytest testsuite/test_responses_session_store.py
```

## Notes

The red proof showed the grandchild request started from the child turn and lost
the parent catalogue context. The green proof verifies the grandchild request
receives parent input, parent assistant output, child input, child assistant
output, and its own input in order.
