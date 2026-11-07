#!/usr/bin/env python3
"""Manage the persistent per-player CODOL Marketplace inventory."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any


TARGET_NAME = "codoMP_client_shipRetail.exe"
DEFAULT_TITLE_ID = 1004
DEFAULT_USER_ID = 0x1100001DEADC0DE
GAME_GET_INVENTORY_RVA = 0xA6B10
GAME_GET_INVENTORY_PREFIX = bytes((0x55, 0x8B, 0xEC, 0x51, 0x80, 0x3D))


def find_game_directory(workspace: Path) -> Path | None:
    for root in workspace.iterdir():
        if not root.is_dir() or not root.name.startswith("Call of Duty Online "):
            continue
        for candidate in root.iterdir():
            if candidate.is_dir() and (candidate / TARGET_NAME).is_file():
                return candidate
    return None


def parse_integer(value: str) -> int:
    try:
        result = int(value, 0)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"invalid integer: {value}") from error
    if result <= 0 or result > 0xFFFFFFFFFFFFFFFF:
        raise argparse.ArgumentTypeError(f"integer is outside the supported range: {value}")
    return result


def inventory_path(args: argparse.Namespace) -> Path:
    if args.state is not None:
        return args.state.resolve()
    if args.game_dir is None:
        raise FileNotFoundError("Could not locate the CODOL game directory; pass --game-dir or --state")
    owner = f"{args.user_id:X}"
    return (
        args.game_dir.resolve()
        / "Ayria"
        / "Assets"
        / "Alwaysoffline"
        / str(args.title_id)
        / owner
        / "Inventory.json"
    )


def load_inventory(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"items": []}
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document.get("items")
    if not isinstance(items, list):
        raise ValueError("inventory document must contain an items array")
    seen: set[int] = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), int):
            raise ValueError(f"invalid inventory item: {item!r}")
        item_id = item["id"]
        if item_id <= 0 or item_id > 0xFFFFFFFF:
            raise ValueError(f"item ID is outside the uint32 range: {item_id}")
        if item_id in seen:
            raise ValueError(f"duplicate item ID: {item_id}")
        seen.add(item_id)
    return document


def write_inventory(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".writing")
    try:
        temporary.write_text(json.dumps(document, indent=2) + "\n", encoding="ascii")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def print_inventory(path: Path, document: dict[str, Any]) -> None:
    print(f"Inventory: {path}")
    items = document["items"]
    print(f"Items: {len(items)}")
    for item in items:
        details = []
        if item.get("type"):
            details.append(str(item["type"]))
        if item.get("label"):
            details.append(str(item["label"]))
        suffix = f" ({', '.join(details)})" if details else ""
        print(f"  {item['id']}{suffix}")


def seed_inventory(source: Path, path: Path, replace: bool) -> int:
    source = source.resolve()
    seed = load_inventory(source)
    current = {"items": []} if replace else load_inventory(path)
    existing = {item["id"] for item in current["items"]}
    added = 0
    for item in seed["items"]:
        if item["id"] not in existing:
            current["items"].append(item)
            existing.add(item["id"])
            added += 1
    write_inventory(path, current)
    print(f"Seeded {added} item(s): {path}")
    return 0


def add_items(path: Path, item_ids: list[int], quantity: int, custom_source_type: int) -> int:
    document = load_inventory(path)
    existing = {item["id"]: item for item in document["items"]}
    added = 0
    for item_id in item_ids:
        if item_id in existing:
            existing[item_id]["quantity"] = quantity
            existing[item_id]["customSourceType"] = custom_source_type
            continue
        item = {
            "id": item_id,
            "quantity": quantity,
            "customSourceType": custom_source_type,
        }
        document["items"].append(item)
        existing[item_id] = item
        added += 1
    write_inventory(path, document)
    print(f"Added {added}, updated {len(item_ids) - added} item(s): {path}")
    return 0


def remove_items(path: Path, item_ids: list[int]) -> int:
    document = load_inventory(path)
    remove = set(item_ids)
    before = len(document["items"])
    document["items"] = [item for item in document["items"] if item["id"] not in remove]
    write_inventory(path, document)
    print(f"Removed {before - len(document['items'])} item(s): {path}")
    return 0


def refresh_game() -> int:
    try:
        import frida
    except ImportError:
        print("Frida is required for refresh; install tools/runtime/requirements-codol.txt", file=sys.stderr)
        return 2

    device = frida.get_local_device()
    matches = [process for process in device.enumerate_processes() if process.name.casefold() == TARGET_NAME.casefold()]
    if not matches:
        print(f"No running {TARGET_NAME} process was found.", file=sys.stderr)
        return 2
    process = max(matches, key=lambda value: value.pid)
    session = device.attach(process.pid)
    finished = threading.Event()
    result: dict[str, Any] = {}
    source = f"""
'use strict';
try {{
    const target = Process.mainModule.base.add({GAME_GET_INVENTORY_RVA});
    const expected = {list(GAME_GET_INVENTORY_PREFIX)};
    for (let i = 0; i < expected.length; ++i) {{
        if (target.add(i).readU8() !== expected[i])
            throw new Error('CODOL inventory refresh signature mismatch');
    }}
    const refresh = new NativeFunction(target, 'bool', []);
    send({{ok: true, requested: refresh()}});
}} catch (error) {{
    send({{ok: false, error: error.stack || error.message}});
}}
"""
    script = session.create_script(source)

    def on_message(message: dict[str, Any], _data: bytes | None) -> None:
        if message.get("type") == "send" and isinstance(message.get("payload"), dict):
            result.update(message["payload"])
        else:
            result.update({"ok": False, "error": repr(message)})
        finished.set()

    script.on("message", on_message)
    try:
        script.load()
        if not finished.wait(10.0):
            print("Timed out waiting for the game inventory refresh.", file=sys.stderr)
            return 3
    finally:
        try:
            script.unload()
        except frida.InvalidOperationError:
            pass
        session.detach()
    if not result.get("ok"):
        print(f"Inventory refresh failed: {result.get('error', 'unknown error')}", file=sys.stderr)
        return 3
    print(f"Requested CODOL inventory refresh in PID {process.pid}: {result['requested']}")
    return 0 if result.get("requested") else 4


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=find_game_directory(repository.parent))
    parser.add_argument("--state", type=Path, help="Override the persistent Inventory.json path")
    parser.add_argument("--title-id", type=parse_integer, default=DEFAULT_TITLE_ID)
    parser.add_argument("--user-id", type=parse_integer, default=DEFAULT_USER_ID)
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("path")
    subparsers.add_parser("list")
    seed = subparsers.add_parser("seed")
    seed.add_argument("source", type=Path, help="Inventory JSON to merge")
    seed.add_argument("--replace", action="store_true")
    add = subparsers.add_parser("add")
    add.add_argument("ids", nargs="+", type=parse_integer)
    add.add_argument("--quantity", type=parse_integer, default=1)
    add.add_argument("--custom-source-type", type=int, choices=range(256), default=0, metavar="0..255")
    remove = subparsers.add_parser("remove")
    remove.add_argument("ids", nargs="+", type=parse_integer)
    subparsers.add_parser("clear")
    subparsers.add_parser("refresh")
    parser.set_defaults(repository=repository)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.action == "refresh":
        return refresh_game()
    try:
        path = inventory_path(args)
        if args.action == "path":
            print(path)
            return 0
        if args.action == "seed":
            return seed_inventory(args.source, path, args.replace)
        if args.action == "add":
            return add_items(path, args.ids, args.quantity, args.custom_source_type)
        if args.action == "remove":
            return remove_items(path, args.ids)
        if args.action == "clear":
            write_inventory(path, {"items": []})
            print(f"Cleared inventory: {path}")
            return 0
        print_inventory(path, load_inventory(path))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Inventory operation failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
