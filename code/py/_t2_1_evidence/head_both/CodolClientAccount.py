#!/usr/bin/env python3
"""Create an isolated local CODOL test account from an existing player seed."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


COPIED_PLAYER_FILES = (
    "Inventory.json",
    "Privateprofile",
    "Publicprofile",
    "the.json",
)


def normalize_user_id(value: str) -> str:
    text = value.strip()
    if text.lower().startswith("0x"):
        text = text[2:]
    user_id = int(text, 16)
    if not user_id or user_id > 0xFFFFFFFFFFFFFFFF:
        raise ValueError("user ID must be a nonzero 64-bit hexadecimal value")
    if user_id <= 0xFFFFFFFF:
        user_id |= 0x0110000100000000
    return f"{user_id:016X}"


def user_id_directory(value: str) -> str:
    return f"{int(normalize_user_id(value), 16):X}"


def validate_display_name(value: str) -> str:
    encoded = value.encode("ascii")
    if not encoded or len(encoded) > 16 or any(byte < 0x20 or byte > 0x7E for byte in encoded):
        raise ValueError("display name must contain 1 to 16 printable ASCII bytes")
    return value


def seed_account(
    player_root: Path,
    source_user_id: str,
    target_user_id: str,
    display_name: str,
) -> Path:
    source_id = normalize_user_id(source_user_id)
    target_id = normalize_user_id(target_user_id)
    validate_display_name(display_name)
    if source_id == target_id:
        raise ValueError("source and target user IDs must be different")

    source = player_root / user_id_directory(source_id)
    target = player_root / user_id_directory(target_id)
    if not source.is_dir():
        raise FileNotFoundError(f"source player directory does not exist: {source}")
    if target.exists():
        raise FileExistsError(f"target player directory already exists: {target}")

    missing = [name for name in COPIED_PLAYER_FILES if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError("source player state is incomplete: " + ", ".join(missing))

    target.mkdir(parents=False)
    try:
        for name in COPIED_PLAYER_FILES:
            shutil.copy2(source / name, target / name)
        (target / "Identity.json").write_text(
            json.dumps(
                {"schemaVersion": 1, "displayName": display_name},
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--player-root", required=True, type=Path)
    parser.add_argument("--source-user-id", required=True)
    parser.add_argument("--target-user-id", required=True)
    parser.add_argument("--display-name", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        target = seed_account(
            args.player_root.resolve(),
            args.source_user_id,
            args.target_user_id,
            args.display_name,
        )
    except (OSError, ValueError) as error:
        print(f"Could not seed CODOL test account: {error}")
        return 2
    print(f"Seeded isolated CODOL test account: {target}")
    print(
        "Launch identity: OLMOD_CLIENT_INSTANCE=2 "
        f"OLMOD_PLATFORM_USER_ID={normalize_user_id(args.target_user_id)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
