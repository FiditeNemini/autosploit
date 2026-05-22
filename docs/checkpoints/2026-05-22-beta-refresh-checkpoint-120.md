# Checkpoint 120: Agent Search Context Proof

## Scope

- Prove deployed agents can use `search_context` inside their own autonomous
  tool loop.
- Make a newly deployed agent able to retrieve shared main-session parsed
  catalogue facts while still keeping its own result store.
- Expose per-agent tool outputs through `/state.agents.details` so agent tool
  behavior is inspectable without switching UI state.

## Changes

- Added `scripts/agent-search-context-proof.py`.
- Agent context lookup now merges main-session parsed results with the agent's
  local result store when building dynamic context for deployed agents.
- `/state.agents.details[*].toolOutputs` exposes bounded per-agent tool output
  metadata for proof and status surfaces.
- Updated the system review and flow inventory so deployed-agent
  `search_context` usage is part of the repeatable QA matrix.

## Proof

Command:

```bash
python3 scripts/agent-search-context-proof.py
```

Result:

- The proof first failed because the deployed agent's `search_context` output
  did not expose parsed main-session attribution facts.
- After wiring shared catalogue lookup for agents, the proof passed and
  verified:
  - the agent runs in forced autopilot;
  - `search_context` is exposed in the agent's tool schema list;
  - the agent autonomously executes `search_context`;
  - the tool output includes `[post.attribution]`, `qa-linux-01`, `www-data`,
    and `linpeas-host`;
  - the next mock model request receives those retrieved context facts.

## Boundary

This is a deterministic mock-engine proof of agent loop/context plumbing. It
does not replace real-model autonomous task proof or external binary execution
proofs.
