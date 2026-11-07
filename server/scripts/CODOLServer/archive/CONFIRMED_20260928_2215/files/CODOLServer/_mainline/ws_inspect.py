#!/usr/bin/env python3
"""Read-only inspection helper for the CODOL launch workspace.

This exists because the current Codex shell wraps commands through cmd.exe in a
way that mangles quoted Python/PowerShell one-liners on this machine.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def print_file(path: Path, max_bytes: int) -> None:
    print(f"===== {path} =====")
    if not path.exists():
        print("[missing]")
        return
    data = path.read_bytes()
    if len(data) > max_bytes:
        print(f"[truncated to {max_bytes} of {len(data)} bytes]")
        data = data[:max_bytes]
    print(data.decode("utf-8", errors="replace"))


def print_slice(path: Path, start: int, end: int) -> None:
    print(f"===== {path}:{start}:{end} =====")
    if not path.exists():
        print("[missing]")
        return
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    lo = max(1, start)
    hi = min(len(lines), end)
    for lineno in range(lo, hi + 1):
        print(f"{lineno}: {lines[lineno - 1]}")


def list_dir(path: Path) -> None:
    print(f"===== dir {path} =====")
    if not path.is_dir():
        print("[missing]")
        return
    entries = []
    for child in path.iterdir():
        try:
            stat = child.stat()
        except OSError:
            continue
        entries.append((stat.st_mtime, child.is_dir(), stat.st_size, child.name))
    for mtime, is_dir, size, name in sorted(entries, reverse=True):
        kind = "d" if is_dir else "f"
        print(f"{mtime:10.0f} {kind} {size:12d} {name}")


def list_processes(patterns: list[str]) -> None:
    print("===== processes =====")
    try:
        raw = subprocess.check_output(
            ["tasklist", "/fo", "csv", "/v"],
            stderr=subprocess.STDOUT,
        )
    except Exception as exc:
        print(f"[tasklist failed: {exc}]")
        return
    text = raw.decode("mbcs", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        print("[empty tasklist]")
        return
    header = rows[0]
    lowered = [p.lower() for p in patterns]
    for row in rows[1:]:
        if not row:
            continue
        image = row[0].lower()
        if any(p in image for p in lowered):
            picked = row[:9]
            print(" | ".join(picked))


def list_ports() -> None:
    print("===== listening ports =====")
    for command in (["netstat", "-ano", "-p", "tcp"],):
        try:
            raw = subprocess.check_output(command, stderr=subprocess.STDOUT)
        except Exception as exc:
            print(f"[{command[0]} failed: {exc}]")
            continue
        text = raw.decode("mbcs", errors="replace")
        for line in text.splitlines():
            if "LISTENING" in line.upper() or "LISTEN" in line.upper():
                print(line.rstrip())


def find_files() -> None:
    print("===== candidate files =====")
    candidates = [
        ROOT / "CODOLServer" / "HANDOFF_20260927_DYNAMIC_CAPTURE.md",
        ROOT / "CODOLServer" / "CODOL_SERVER_OPERATIONS_MANUAL.md",
        ROOT / "CODOLServer" / "_mainline" / "auto_lobby_loop.py",
        ROOT / "CODOLServer" / "lobby_server" / "lobby_probe_server.py",
        ROOT / "CODOLServer" / "lobby_server" / "lobby_socket_server.py",
        ROOT / "CODOLServer" / "lobby_server" / "lobby_response.json",
        ROOT / "run_codol_001" / "sandbox_ifs1_20260923" / "dwauth.ini",
        ROOT / "run_codol_001" / "sandbox_ifs1_20260923" / "iips.ini",
    ]
    for path in candidates:
        exists = path.exists()
        size = path.stat().st_size if exists else -1
        print(f"{exists} {size:10d} {path}")


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", action="store_true")
    parser.add_argument("--manual", action="store_true")
    parser.add_argument("--files", action="store_true")
    parser.add_argument("--dir", action="append", default=[])
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--slice", action="append", default=[],
                        help="PATH:START:END (1-based, inclusive)")
    parser.add_argument("--proc", action="append", default=[])
    parser.add_argument("--ports", action="store_true")
    parser.add_argument("--max-bytes", type=int, default=120_000)
    parser.add_argument("--limit", type=int, default=0,
                        help="limit directory listing entries (0 = all)")
    args = parser.parse_args()

    if args.files:
        find_files()
    if args.handoff:
        print_file(ROOT / "CODOLServer" / "HANDOFF_20260927_DYNAMIC_CAPTURE.md", args.max_bytes)
    if args.manual:
        print_file(ROOT / "CODOLServer" / "CODOL_SERVER_OPERATIONS_MANUAL.md", args.max_bytes)
    for item in args.dir:
        if args.limit:
            path = Path(item)
            print(f"===== dir {path} (first {args.limit}) =====")
            if path.is_dir():
                entries = []
                for child in path.iterdir():
                    try:
                        stat = child.stat()
                    except OSError:
                        continue
                    entries.append((stat.st_mtime, child.is_dir(),
                                    stat.st_size, child.name))
                for mtime, is_dir, size, name in sorted(entries,
                                                        reverse=True)[:args.limit]:
                    print(f"{mtime:10.0f} {'d' if is_dir else 'f'} "
                          f"{size:12d} {name}")
            else:
                print("[missing]")
        else:
            list_dir(Path(item))
    for item in args.file:
        print_file(Path(item), args.max_bytes)
    for item in args.slice:
        path_text, start_text, end_text = item.rsplit(":", 2)
        print_slice(Path(path_text), int(start_text), int(end_text))
    patterns = args.proc or [
        "codo",
        "aboprobe",
        "tp3",
        "tqm",
        "iips",
        "wegame",
        "tcls",
        "python",
        "elevated",
    ]
    if args.proc is not None:
        list_processes(patterns)
    if args.ports:
        list_ports()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
