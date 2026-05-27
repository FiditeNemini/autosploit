#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run() -> None:
    proc = subprocess.run(
        [
            "swift",
            "build",
            "--package-path",
            "ExploitBot",
            "-c",
            "release",
            "-Xswiftc",
            "-warnings-as-errors",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
    )
    if proc.returncode != 0:
        tail = "\n".join(proc.stdout.splitlines()[-80:])
        raise AssertionError(f"release warning-clean build failed:\n{tail}")
    if "warning:" in proc.stdout:
        tail = "\n".join(line for line in proc.stdout.splitlines() if "warning:" in line)
        raise AssertionError(f"release build still emitted warnings:\n{tail}")
    print("swift-warning-clean proof passed")


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, subprocess.TimeoutExpired) as exc:
        print(f"swift-warning-clean proof failed: {exc}", flush=True)
        raise SystemExit(1)
