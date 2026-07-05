from __future__ import annotations

import contextlib
import os
import shutil
import time
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK_PATH = ROOT / ".proof-locks" / "app-proof-lifecycle.lock"


def _lock_path() -> Path:
    override = os.environ.get("EXPLOITBOT_APP_PROOF_LOCK_PATH")
    return Path(override) if override else DEFAULT_LOCK_PATH


def _owner_pid(lock_path: Path) -> int | None:
    owner_file = lock_path / "owner"
    if not owner_file.is_file():
        return None
    for line in owner_file.read_text(encoding="utf-8", errors="replace").splitlines():
        key, _, value = line.partition("=")
        if key == "pid" and value.strip().isdigit():
            return int(value.strip())
    return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _owner_missing_seconds(lock_path: Path) -> float:
    try:
        return max(0.0, time.time() - lock_path.stat().st_mtime)
    except FileNotFoundError:
        return 0.0


def _stale_lock(lock_path: Path) -> bool:
    pid = _owner_pid(lock_path)
    if pid is None:
        return _owner_missing_seconds(lock_path) >= 30.0
    return not _pid_alive(pid)


@contextlib.contextmanager
def app_proof_lock(name: str, timeout: float = 900.0) -> Iterator[None]:
    lock_path = _lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout
    announced_wait = False
    acquired = False

    while not acquired:
        try:
            lock_path.mkdir()
            acquired = True
        except FileExistsError:
            if _stale_lock(lock_path):
                shutil.rmtree(lock_path, ignore_errors=True)
                continue
            if not announced_wait:
                print(f"Another app-backed proof is active; waiting for {lock_path}...", flush=True)
                announced_wait = True
            if time.time() >= deadline:
                owner = ""
                owner_file = lock_path / "owner"
                if owner_file.is_file():
                    owner = owner_file.read_text(encoding="utf-8", errors="replace")
                raise TimeoutError(f"timed out waiting for app proof lifecycle lock {lock_path}\n{owner}")
            time.sleep(1.0)

    owner_file = lock_path / "owner"
    owner_file.write_text(
        "\n".join(
            [
                f"pid={os.getpid()}",
                f"name={name}",
                f"startedAt={time.strftime('%Y-%m-%dT%H:%M:%S%z')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        yield
    finally:
        if _owner_pid(lock_path) == os.getpid():
            shutil.rmtree(lock_path, ignore_errors=True)
