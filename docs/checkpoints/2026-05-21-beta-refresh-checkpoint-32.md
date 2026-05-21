# Beta Refresh Checkpoint 32

Date: 2026-05-21

## Scope

- Fixed the Python engine package dependency contract so FastAPI server routes using form upload types can import in a fresh environment.
- Added a `dev` optional dependency group for the engine test runner.
- Added a `uv.lock` lockfile for reproducible engine dependency resolution.

## Files

- `ExploitBotEngine/pyproject.toml`
- `ExploitBotEngine/uv.lock`

## Verification

- `PYTHONPATH=. uv run --extra dev pytest -q`

## Result

- `22 passed, 3 warnings`

## Notes

- Before this checkpoint, server-import tests failed because `python-multipart` was not declared even though FastAPI validates multipart route dependencies at import time.
- The warnings are existing dependency/runtime warnings: MLX SWIG module metadata and Pydantic v2 class-based config deprecation.
