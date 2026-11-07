#!/usr/bin/env python3
"""Enable or restore CODOL hostname matching in Alwaysoffline.Localnet32."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path


ORIGINAL_SHA256 = "A4A7230C03FDFF7A100668E137B99DD8639B7E4079970DA5DF7900A32A84DCF2"
PATCHED_SHA256 = "BBA68F42759BD74B95A3C216A96153B6B8F80094A1923618CCD0DE73A059359A"
USERNAME_OFFSET = 0x181568
USERNAME_SLOT_SIZE = 14
DEFAULT_USERNAME_SLOT = b"Alwaysoffline\0"
LITERAL_OFFSET = 0x181590
ORIGINAL_LITERAL = b"stun.\0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def normalized_sha256(data: bytes) -> str:
    normalized = bytearray(data)
    normalized[USERNAME_OFFSET : USERNAME_OFFSET + USERNAME_SLOT_SIZE] = DEFAULT_USERNAME_SLOT
    return hashlib.sha256(normalized).hexdigest().upper()


def find_game_directory(workspace: Path) -> Path | None:
    for root in workspace.iterdir():
        if not root.is_dir() or not root.name.startswith("Call of Duty Online "):
            continue
        for candidate in root.iterdir():
            if candidate.is_dir() and (candidate / "codoMP_client_shipRetail.exe").is_file():
                return candidate
    return None


def atomic_write(path: Path, data: bytes, expected_hash: str) -> None:
    temporary = path.with_name(path.name + ".codol-patching")
    try:
        temporary.write_bytes(data)
        if sha256(temporary) != expected_hash:
            raise RuntimeError("Temporary output did not match the expected hash")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--game-dir",
        type=Path,
        default=find_game_directory(repository.parent),
        help="Defaults to the CODOL 3.3.3.3 directory under the workspace",
    )
    parser.add_argument("--restore", action="store_true")
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Patch in place without adding an Ayria/Backups directory",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.game_dir is None:
        print("Could not locate the CODOL game directory; pass --game-dir.", file=sys.stderr)
        return 2

    game_directory = args.game_dir.resolve()
    plugin = game_directory / "Ayria" / "Plugins" / "Alwaysoffline.Localnet32"
    backup = game_directory / "Ayria" / "Backups" / "Alwaysoffline.Localnet32"
    legacy_backup = plugin.with_name(plugin.name + ".codol-original")
    if not plugin.is_file():
        print(f"Alwaysoffline plugin not found: {plugin}", file=sys.stderr)
        return 2

    if legacy_backup.is_file():
        if normalized_sha256(legacy_backup.read_bytes()) != ORIGINAL_SHA256:
            print(f"Existing legacy backup does not match the known original: {legacy_backup}", file=sys.stderr)
            return 2
        backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.is_file() and normalized_sha256(backup.read_bytes()) != ORIGINAL_SHA256:
            print(f"Existing backup does not match the known original: {backup}", file=sys.stderr)
            return 2
        if backup.is_file():
            legacy_backup.unlink()
        else:
            os.replace(legacy_backup, backup)
        print(f"Moved runtime-visible backup out of the plugin directory: {backup}")

    if not args.no_backup:
        backup.parent.mkdir(parents=True, exist_ok=True)

    data = bytearray(plugin.read_bytes())
    current_hash = normalized_sha256(data)
    if args.restore:
        if current_hash == ORIGINAL_SHA256:
            print("CODOL STUN proxy fix is already disabled.")
            return 0
        if current_hash != PATCHED_SHA256:
            print(f"Refusing to restore an unknown plugin build: {current_hash}", file=sys.stderr)
            return 2
        data[LITERAL_OFFSET + 4] = ord(".")
        expected_hash = hashlib.sha256(data).hexdigest().upper()
        atomic_write(plugin, data, expected_hash)
        print(f"Restored original Alwaysoffline plugin: {plugin}")
        return 0

    if current_hash == PATCHED_SHA256:
        print("CODOL STUN proxy fix is already enabled.")
        return 0
    if current_hash != ORIGINAL_SHA256:
        print(f"Refusing to patch an unknown plugin build: {current_hash}", file=sys.stderr)
        return 2

    if data[LITERAL_OFFSET : LITERAL_OFFSET + len(ORIGINAL_LITERAL)] != ORIGINAL_LITERAL:
        print(
            f'Expected "stun." literal was not present at file offset 0x{LITERAL_OFFSET:X}.',
            file=sys.stderr,
        )
        return 2

    occurrences = bytes(data).count(ORIGINAL_LITERAL)
    if occurrences != 1:
        print(f"Expected one matching literal, found {occurrences}.", file=sys.stderr)
        return 2

    if not args.no_backup:
        if backup.is_file():
            if normalized_sha256(backup.read_bytes()) != ORIGINAL_SHA256:
                print(f"Existing backup does not match the known original: {backup}", file=sys.stderr)
                return 2
        else:
            shutil.copy2(plugin, backup)

    data[LITERAL_OFFSET + 4] = 0
    expected_hash = hashlib.sha256(data).hexdigest().upper()
    atomic_write(plugin, data, expected_hash)
    print(f"Enabled CODOL stun1-/stun2- proxy matching: {plugin}")
    if args.no_backup:
        print("No runtime backup was created; use the workspace release copy to restore the plugin.")
    else:
        print(f"Original backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
