# Checkpoint 57 - Split Settings Pages

## Summary

Reworked Settings from one long flat page into a split category layout. The
settings surface now has a left category rail and focused pages for each
configuration area.

## Changes

- Added Settings categories:
  - Engine
  - Model
  - Runtime
  - Context
  - Cache
  - Agents
  - CVE Database
  - Tools
  - Logs
- Moved the existing controls into focused page sections without changing the
  underlying save/restart behavior.
- Added a persistent footer with `Apply & Restart Engine`.
- Split inference logs into their own Settings page instead of hiding them in
  the engine section.
- Kept model-folder-only selection and Qwen/MiniMax support warnings visible in
  the Model page.
- Verified Model and Context category pages visually in the running macOS app.

## Verification

```bash
python3 scripts/live-turn-harness.py
swift build --package-path ExploitBot
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q
```
