#!/usr/bin/env python3
"""Capture and compare reproducible CODOL filesystem/runtime state snapshots."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


TARGET_NAME = "codoMP_client_shipRetail.exe"
FULL_HASH_LIMIT = 32 * 1024 * 1024
SAMPLE_SIZE = 1024 * 1024
EVIDENCE_FILES = (
    "stun.ini",
    "iips.ini",
    "players/config_mp.cfg",
    "IIPS/IIPSClient.ini",
    "IIPS/Progress.ini",
    "IIPS/vodcache/download.db",
)


def find_game_directory(workspace: Path) -> Path | None:
    for root in workspace.iterdir():
        if not root.is_dir() or not root.name.startswith("Call of Duty Online "):
            continue
        for candidate in root.iterdir():
            if candidate.is_dir() and (candidate / TARGET_NAME).is_file():
                return candidate
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sampled_sha256(path: Path, size: int) -> tuple[str, list[int]]:
    offsets = sorted({0, max(0, (size - SAMPLE_SIZE) // 2), max(0, size - SAMPLE_SIZE)})
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for offset in offsets:
            stream.seek(offset)
            block = stream.read(min(SAMPLE_SIZE, size - offset))
            digest.update(offset.to_bytes(8, "little"))
            digest.update(len(block).to_bytes(8, "little"))
            digest.update(block)
    return digest.hexdigest().upper(), offsets


def manifest_entry(root: Path, path: Path) -> dict[str, Any]:
    stat = path.stat()
    relative = path.relative_to(root).as_posix()
    entry: dict[str, Any] = {
        "path": relative,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }
    if stat.st_size <= FULL_HASH_LIMIT or relative.startswith("Ayria/"):
        entry["hash_kind"] = "full"
        entry["sha256"] = sha256_file(path)
    else:
        digest, offsets = sampled_sha256(path, stat.st_size)
        entry["hash_kind"] = "sampled"
        entry["sha256"] = digest
        entry["sample_size"] = SAMPLE_SIZE
        entry["sample_offsets"] = offsets
    return entry


def run_text(command: list[str]) -> str:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    return result.stdout + ("\nSTDERR:\n" + result.stderr if result.stderr else "")


def newest_pid() -> int | None:
    script = (
        f"Get-Process -Name '{Path(TARGET_NAME).stem}' -ErrorAction SilentlyContinue | "
        "Sort-Object StartTime -Descending | Select-Object -First 1 -ExpandProperty Id"
    )
    output = run_text(["powershell", "-NoProfile", "-NonInteractive", "-Command", script]).strip()
    try:
        return int(output)
    except ValueError:
        return None


def capture_runtime(repository: Path, output: Path, pid: int) -> None:
    system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    powershell32 = system_root / "SysWOW64" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if not powershell32.is_file():
        powershell32 = Path("powershell")

    module_script = (
        f"Get-Process -Id {pid} -ErrorAction Stop | Select-Object -ExpandProperty Modules | "
        "Select-Object ModuleName,FileName,ModuleMemorySize | ConvertTo-Json -Depth 3"
    )
    (output / "runtime_modules.json").write_text(
        run_text([str(powershell32), "-NoProfile", "-NonInteractive", "-Command", module_script]),
        encoding="utf-8",
    )
    process_script = (
        f"Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" | "
        "Select-Object ProcessId,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json"
    )
    (output / "runtime_process.json").write_text(
        run_text(["powershell", "-NoProfile", "-NonInteractive", "-Command", process_script]),
        encoding="utf-8",
    )
    netstat = run_text(["netstat", "-ano"])
    matching = [line for line in netstat.splitlines() if line.rstrip().endswith(str(pid))]
    (output / "runtime_network.txt").write_text("\n".join(matching) + "\n", encoding="utf-8")

    screenshot_tool = repository / "tools" / "runtime" / "CaptureCodolWindow.py"
    screenshot = output / "window.png"
    subprocess.run(
        [sys.executable, str(screenshot_tool), "--pid", str(pid), "--output", str(screenshot)],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )


def capture(args: argparse.Namespace) -> int:
    repository: Path = args.repository
    game_directory = args.game_dir.resolve() if args.game_dir else None
    if game_directory is None or not game_directory.is_dir():
        print("Could not locate the CODOL game directory; pass --game-dir.", file=sys.stderr)
        return 2

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    label = "".join(character if character.isalnum() or character in "-_" else "-" for character in args.label)
    output = args.output.resolve() if args.output else repository / "diagnostics" / "snapshots" / f"{stamp}_{label}"
    output.mkdir(parents=True, exist_ok=False)

    started_at = dt.datetime.now(dt.timezone.utc).isoformat()
    entries: list[dict[str, Any]] = []
    total_bytes = 0
    files = (
        item for item in game_directory.rglob("*")
        if item.is_file() and item.suffix.casefold() != ".ifs"
    )
    for path in sorted(files, key=lambda item: str(item).casefold()):
        entry = manifest_entry(game_directory, path)
        entries.append(entry)
        total_bytes += entry["size"]
    with (output / "manifest.jsonl").open("w", encoding="utf-8") as stream:
        for entry in entries:
            stream.write(json.dumps(entry, ensure_ascii=True, separators=(",", ":")) + "\n")

    evidence = output / "files"
    for relative in EVIDENCE_FILES:
        source = game_directory / relative
        if source.is_file():
            target = evidence / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    logs = game_directory / "Ayria" / "Logs"
    if logs.is_dir():
        shutil.copytree(logs, evidence / "Ayria" / "Logs")

    pid = args.pid if args.pid is not None else newest_pid()
    if pid is not None:
        capture_runtime(repository, output, pid)
    git_commit = run_text(["git", "-C", str(repository), "rev-parse", "HEAD"]).strip()
    metadata = {
        "schema_version": 1,
        "label": args.label,
        "started_at": started_at,
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "game_directory": str(game_directory),
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "full_hash_limit": FULL_HASH_LIMIT,
        "sample_size": SAMPLE_SIZE,
        "pid": pid,
        "git_commit": git_commit,
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Captured CODOL state: {output}")
    print(f"Files: {len(entries)}, bytes: {total_bytes}, PID: {pid}")
    return 0


def load_manifest(snapshot: Path) -> dict[str, dict[str, Any]]:
    path = snapshot / "manifest.jsonl"
    return {
        entry["path"]: entry
        for entry in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    }


def compare(args: argparse.Namespace) -> int:
    before = load_manifest(args.before.resolve())
    after = load_manifest(args.after.resolve())
    missing = sorted(before.keys() - after.keys())
    added = sorted(after.keys() - before.keys())
    common = before.keys() & after.keys()
    content_changed = sorted(
        path for path in common
        if before[path]["size"] != after[path]["size"] or before[path]["sha256"] != after[path]["sha256"]
    )
    metadata_changed = sorted(
        path for path in common
        if path not in content_changed and before[path]["mtime_ns"] != after[path]["mtime_ns"]
    )
    result = {
        "before": str(args.before.resolve()),
        "after": str(args.after.resolve()),
        "missing": missing,
        "added": added,
        "content_changed": content_changed,
        "metadata_only_changed": metadata_changed,
    }
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.resolve().write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if missing or added or content_changed else 0


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)

    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--game-dir", type=Path, default=find_game_directory(repository.parent))
    capture_parser.add_argument("--label", default="snapshot")
    capture_parser.add_argument("--output", type=Path)
    capture_parser.add_argument("--pid", type=int)
    capture_parser.set_defaults(handler=capture)

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("before", type=Path)
    compare_parser.add_argument("after", type=Path)
    compare_parser.add_argument("--output", type=Path)
    compare_parser.set_defaults(handler=compare)

    parser.set_defaults(repository=repository)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
