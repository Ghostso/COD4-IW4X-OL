#!/usr/bin/env python3
"""Patch the archived Project Nova backend username for compatibility tests."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


TARGET_NAME = "codoMP_client_shipRetail.exe"
PLUGIN_NAME = "Alwaysoffline.Localnet32"
USERNAME_OFFSET = 0x181568
USERNAME_SLOT_SIZE = 14
DEFAULT_USERNAME = "Alwaysoffline"
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,13}")
FOLLOWING_ANCHOR = b"\0\0demonware.net\0"


def find_game_directory(workspace: Path) -> Path | None:
    for root in workspace.iterdir():
        if not root.is_dir() or not root.name.startswith("Call of Duty Online "):
            continue
        for candidate in root.iterdir():
            if candidate.is_dir() and (candidate / TARGET_NAME).is_file():
                return candidate
    return None


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=find_game_directory(repository.parent))
    parser.add_argument("--username", help="Required unless --restore is used")
    parser.add_argument("--restore", action="store_true", help=f"Restore {DEFAULT_USERNAME}")
    parser.set_defaults(repository=repository)
    return parser.parse_args()


def read_slot(data: bytes) -> str:
    raw = data[USERNAME_OFFSET : USERNAME_OFFSET + USERNAME_SLOT_SIZE]
    name, separator, padding = raw.partition(b"\0")
    if not separator or any(padding):
        raise ValueError("Authentication username slot is not NUL-padded")
    return name.decode("ascii")


def main() -> int:
    args = parse_args()
    if args.game_dir is None:
        print("Could not locate the CODOL game directory; pass --game-dir.", file=sys.stderr)
        return 2

    username = DEFAULT_USERNAME if args.restore else args.username
    if username is None:
        print("Pass --username or use --restore.", file=sys.stderr)
        return 2
    if USERNAME_PATTERN.fullmatch(username) is None:
        print("Username must be 1-13 ASCII letters, digits, dots, underscores, or hyphens.", file=sys.stderr)
        return 2

    plugin = args.game_dir.resolve() / "Ayria" / "Plugins" / PLUGIN_NAME
    if not plugin.is_file():
        print(f"Alwaysoffline plugin not found: {plugin}", file=sys.stderr)
        return 2

    data = bytearray(plugin.read_bytes())
    anchor_offset = USERNAME_OFFSET + USERNAME_SLOT_SIZE
    if data[anchor_offset : anchor_offset + len(FOLLOWING_ANCHOR)] != FOLLOWING_ANCHOR:
        print("Refusing to patch: the authentication string layout is not the known build.", file=sys.stderr)
        return 2
    try:
        previous = read_slot(data)
    except (UnicodeDecodeError, ValueError) as error:
        print(f"Refusing to patch: {error}", file=sys.stderr)
        return 2
    if previous == username:
        print(f"CODOL authentication username is already {username!r}.")
        return 0

    encoded = username.encode("ascii")
    data[USERNAME_OFFSET : USERNAME_OFFSET + USERNAME_SLOT_SIZE] = encoded.ljust(USERNAME_SLOT_SIZE, b"\0")
    temporary = plugin.with_name(plugin.name + ".codol-identity-deploying")
    try:
        temporary.write_bytes(data)
        if read_slot(temporary.read_bytes()) != username:
            raise RuntimeError("Temporary plugin did not preserve the requested username")
        os.replace(temporary, plugin)
    except PermissionError:
        print(
            f"The running game has locked {PLUGIN_NAME}; configuration is ready, "
            "but deployment must be repeated after the process exits.",
            file=sys.stderr,
        )
        return 3
    finally:
        temporary.unlink(missing_ok=True)

    print(f"Changed CODOL authentication username: {previous!r} -> {username!r}")
    print(f"Patched plugin: {plugin}")
    print("The new name is used on the next authentication/login.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
