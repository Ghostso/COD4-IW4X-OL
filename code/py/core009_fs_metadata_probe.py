from __future__ import annotations

"""CORE-009 low-interference filesystem metadata probe.

Only paths, sizes, and timestamps are captured. File contents are never read.
The formal 12-run CSV matrix is restored after this supplemental probe.
"""

import csv
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GAME = ROOT / "COD OL"
OBSERVER = ROOT / "_core009_observer" / "bin" / "Release" / "net48" / "core009_boundary_observation.exe"
OUT = ROOT / "exe_core009_fs_delta.csv"
WATCH_DIRS = [GAME, GAME / "Logs", GAME / "TenproxyLog", GAME / "TimeLog"]
MATRIX = [
    "runs", "registers", "stack", "state_delta", "module_delta",
    "thread_delta", "commandline_matrix", "contract_matrix",
]


def snapshot() -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    seen: set[Path] = set()
    for base in WATCH_DIRS:
        if not base.is_dir() or base in seen:
            continue
        seen.add(base)
        iterator = base.glob("*") if base == GAME else base.rglob("*")
        for path in iterator:
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(GAME).as_posix()
                stat = path.stat()
                stamp = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="milliseconds")
                result[rel] = (stat.st_size, stamp)
            except OSError:
                continue
    return result


def main() -> int:
    if not OBSERVER.is_file():
        raise SystemExit(f"observer missing: {OBSERVER}")
    backups: dict[str, bytes] = {}
    for kind in MATRIX:
        path = ROOT / f"exe_core009_{kind}.csv"
        if path.is_file():
            backups[kind] = path.read_bytes()
    before = snapshot()
    completed = subprocess.run(
        [str(OBSERVER), "--case=A", "--repeat=9"],
        cwd=ROOT, text=True, capture_output=True, timeout=30,
    )
    after = snapshot()
    rows = []
    for rel in sorted(set(before) | set(after)):
        b = before.get(rel)
        a = after.get(rel)
        if b == a:
            continue
        rows.append({
            "path": rel,
            "operation_category": "create" if b is None else "metadata_or_size_delta",
            "before_size": "" if b is None else b[0],
            "after_size": "" if a is None else a[0],
            "before_timestamp_utc": "" if b is None else b[1],
            "after_timestamp_utc": "" if a is None else a[1],
        })
    with OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        fields = ["path", "operation_category", "before_size", "after_size", "before_timestamp_utc", "after_timestamp_utc"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    for kind, data in backups.items():
        (ROOT / f"exe_core009_{kind}.csv").write_bytes(data)
    for path in ROOT.glob("exe_core009_*_A_9.csv"):
        path.unlink(missing_ok=True)
    print(f"FS_METADATA_DELTA_ROWS={len(rows)}")
    print(completed.stdout, end="")
    if completed.returncode != 0:
        print(completed.stderr, end="")
        return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
