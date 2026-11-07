#!/usr/bin/env python3
"""Inspect or remove stale Frida extraction directories."""

from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPOSITORY_ROOT / ".runtime" / "frida"


def directory_size(path: Path) -> int:
    total = 0
    for candidate in path.rglob("*"):
        try:
            if candidate.is_file():
                total += candidate.stat().st_size
        except OSError:
            continue
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--max-age-hours", type=float, default=24.0)
    parser.add_argument("--apply", action="store_true", help="remove matching directories")
    args = parser.parse_args()

    if args.max_age_hours < 0:
        parser.error("--max-age-hours must be non-negative")

    root = args.root.resolve()
    if not root.is_dir():
        print(f"Runtime directory does not exist: {root}")
        return 0

    cutoff = time.time() - args.max_age_hours * 60 * 60
    candidates: list[tuple[Path, int]] = []
    for path in root.glob("frida-*"):
        try:
            if path.is_dir() and path.stat().st_mtime < cutoff:
                candidates.append((path, directory_size(path)))
        except OSError:
            continue

    total = sum(size for _, size in candidates)
    action = "Removing" if args.apply else "Would remove"
    print(f"{action} {len(candidates)} directories ({total / 1024**3:.2f} GiB) under {root}")
    if not args.apply:
        print("Pass --apply after checking the resolved root.")
        return 0

    failures = 0
    for path, _ in candidates:
        try:
            shutil.rmtree(path)
        except OSError as error:
            failures += 1
            print(f"Could not remove {path}: {error}")
    print(f"Removed {len(candidates) - failures}; failed {failures}.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
