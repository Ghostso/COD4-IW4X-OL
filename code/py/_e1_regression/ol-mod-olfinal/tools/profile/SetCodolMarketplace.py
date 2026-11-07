#!/usr/bin/env python3
"""Deploy the experimental CODOL Marketplace asset for compatibility tests."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


TARGET_NAME = "codoMP_client_shipRetail.exe"


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
    parser.add_argument("--source", type=Path, help="Historical Marketplace JSON input")
    parser.add_argument("--remove", action="store_true")
    parser.set_defaults(repository=repository)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.game_dir is None:
        print("Could not locate the CODOL game directory; pass --game-dir.", file=sys.stderr)
        return 2

    target = (
        args.game_dir.resolve()
        / "Ayria" / "Assets" / "Alwaysoffline" / "1004" / "Server" / "Marketplace"
    )
    if args.remove:
        target.unlink(missing_ok=True)
        print(f"Removed CODOL Marketplace asset: {target}")
        return 0

    if args.source is None:
        print("The historical Marketplace input is no longer bundled; pass --source.", file=sys.stderr)
        return 2
    source = args.source.resolve()

    inventory = json.loads(source.read_text(encoding="utf-8"))
    if not all(key in inventory for key in ("Wallets", "Loot", "Entitlements")):
        print(f"Invalid Marketplace asset: {source}", file=sys.stderr)
        return 2
    for item in inventory["Loot"]:
        if set(item) != {"ID"} or not isinstance(item["ID"], int):
            print(f"Invalid Loot entry: {item!r}", file=sys.stderr)
            return 2

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".codol-deploying")
    temporary.write_text(json.dumps(inventory, separators=(",", ":")), encoding="ascii")
    os.replace(temporary, target)
    print(f"Deployed {len(inventory['Loot'])} experimental CODOL Loot entries: {target}")
    for item in inventory["Loot"]:
        print(f"  {item['ID']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
