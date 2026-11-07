#!/usr/bin/env python3
"""Verify a CODOL evidence archive against its CHECKSUMS.txt.

Usage:
  python -X utf8 CODOLServer/_mainline/archive_verify.py <archive-dir>
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path


def configure_stdio() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> int:
    configure_stdio()
    if len(sys.argv) < 2:
        print("usage: archive_verify.py <archive-dir>")
        return 2
    archive = Path(sys.argv[1])
    sums = archive / "CHECKSUMS.txt"
    if not sums.is_file():
        print("missing CHECKSUMS.txt in", archive)
        return 2

    ok = bad = absent = 0
    for line in sums.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, rel = line.partition("  ")
        # CHECKSUMS paths are relative to the project root; strip the
        # top-level folder so they resolve inside the archive.
        candidate = archive / "files" / rel
        if not candidate.is_file():
            candidate = archive / rel
        if not candidate.is_file():
            parts = Path(rel).parts
            for i in range(1, len(parts)):
                trial = archive.joinpath(*parts[i:])
                if trial.is_file():
                    candidate = trial
                    break
        if not candidate.is_file():
            print("MISSING ", rel)
            absent += 1
            continue
        if sha256(candidate) == digest:
            ok += 1
        else:
            print("MISMATCH", rel)
            bad += 1

    print(f"verified={ok} mismatch={bad} absent={absent}")
    return 0 if bad == 0 and absent == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
