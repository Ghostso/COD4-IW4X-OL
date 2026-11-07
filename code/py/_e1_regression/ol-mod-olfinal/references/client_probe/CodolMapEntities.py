#!/usr/bin/env python3
"""Read the loaded CODOL map entity asset and list spawn candidates."""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "runtime"))
from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


IMAGE_NAME = "codoMP_client_shipRetail.exe"
DB_FIND_XASSET_HEADER_RVA = 0x9E7D0
ASSET_TYPE_MAP_ENTS = 19
ASSET_TYPE_ADDON_MAP_ENTS = 42
TOKEN_PATTERN = re.compile(r'\{|\}|"(?:\\.|[^"\\])*"', re.DOTALL)


def find_pid(device: frida.core.Device, requested: int | None) -> int:
    if requested is not None:
        return requested
    matches = [
        process.pid
        for process in device.enumerate_processes()
        if process.name.lower() == IMAGE_NAME.lower()
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {IMAGE_NAME} process, found {len(matches)}")
    return matches[0]


def decode_quoted(token: str) -> str:
    try:
        return json.loads(token)
    except json.JSONDecodeError:
        return token[1:-1].replace(r'\"', '"').replace(r"\\", "\\")


def parse_entities(text: str) -> list[dict[str, str]]:
    tokens = TOKEN_PATTERN.findall(text)
    entities: list[dict[str, str]] = []
    index = 0
    while index < len(tokens):
        if tokens[index] != "{":
            raise ValueError(f"expected entity opening brace at token {index}")
        index += 1
        entity: dict[str, str] = {}
        while index < len(tokens) and tokens[index] != "}":
            if index + 1 >= len(tokens) or not tokens[index].startswith('"'):
                raise ValueError(f"expected quoted entity key at token {index}")
            if not tokens[index + 1].startswith('"'):
                raise ValueError(f"expected quoted entity value at token {index + 1}")
            entity[decode_quoted(tokens[index])] = decode_quoted(tokens[index + 1])
            index += 2
        if index >= len(tokens):
            raise ValueError("unterminated map entity")
        entities.append(entity)
        index += 1
    return entities


def parse_vector(value: str | None) -> list[float] | None:
    if value is None:
        return None
    parts = value.split()
    if len(parts) != 3:
        return None
    try:
        return [float(part) for part in parts]
    except ValueError:
        return None


def spawn_candidates(entities: list[dict[str, str]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for index, entity in enumerate(entities):
        classname = entity.get("classname", "")
        if classname == "worldspawn" or (
            "spawn" not in classname.lower() and classname != "info_player_start"
        ):
            continue
        candidates.append(
            {
                "index": index,
                "classname": classname,
                "origin": parse_vector(entity.get("origin")),
                "angles": parse_vector(entity.get("angles")),
                "angle": entity.get("angle"),
                "team": entity.get("team"),
                "targetname": entity.get("targetname"),
            }
        )
    return candidates


def build_script(map_name: str) -> str:
    requests = [
        {"type": ASSET_TYPE_MAP_ENTS, "name": f"maps/mp/{map_name}.d3dbsp"},
        {"type": ASSET_TYPE_MAP_ENTS, "name": f"maps/mp/{map_name}.mapents"},
        {"type": ASSET_TYPE_MAP_ENTS, "name": map_name},
        {"type": ASSET_TYPE_ADDON_MAP_ENTS, "name": f"maps/mp/{map_name}.mapents"},
    ]
    return f"""
'use strict';

const module = Process.getModuleByName({json.dumps(IMAGE_NAME)});
const dbFind = new NativeFunction(
    module.base.add({DB_FIND_XASSET_HEADER_RVA}),
    'pointer',
    ['int', 'pointer', 'int']);
const requests = {json.dumps(requests)};

setImmediate(function() {{
    const attempts = [];
    for (const request of requests) {{
        const name = Memory.allocUtf8String(request.name);
        const asset = dbFind(request.type, name, 0);
        if (asset.isNull()) {{
            attempts.push({{ type: request.type, name: request.name, found: false }});
            continue;
        }}
        let assetName = null;
        let entityString = ptr(0);
        let entityChars = 0;
        try {{
            assetName = asset.readPointer().readCString();
            entityString = asset.add(4).readPointer();
            entityChars = asset.add(8).readS32();
        }} catch (error) {{
            attempts.push({{
                type: request.type,
                name: request.name,
                found: true,
                asset: asset.toString(),
                error: error.message
            }});
            continue;
        }}
        if (entityString.isNull() || entityChars <= 0 || entityChars > 16 * 1024 * 1024) {{
            attempts.push({{
                type: request.type,
                name: request.name,
                found: true,
                asset: asset.toString(),
                asset_name: assetName,
                entity_chars: entityChars,
                error: 'invalid entity string bounds'
            }});
            continue;
        }}
        send({{
            event: 'map_entities',
            request: request,
            asset: asset.toString(),
            asset_name: assetName,
            entity_string: entityString.toString(),
            entity_chars: entityChars,
            attempts: attempts
        }}, entityString.readByteArray(entityChars));
        return;
    }}
    send({{ event: 'not_found', attempts: attempts }});
}});
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--map-name", default="mp_crash_tropical")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    device = frida.get_local_device()
    pid = find_pid(device, args.pid)
    done = threading.Event()
    result: dict[str, Any] = {}
    entity_bytes: bytes | None = None
    session = device.attach(pid)
    script = session.create_script(build_script(args.map_name))

    def on_message(message: dict[str, Any], data: bytes | None) -> None:
        nonlocal entity_bytes
        if message.get("type") == "send":
            result.update(message.get("payload", {}))
            entity_bytes = data
        else:
            result.update(event="frida_error", message=message)
        done.set()

    script.on("message", on_message)
    try:
        script.load()
        if not done.wait(args.timeout):
            raise TimeoutError(f"map entity lookup timed out after {args.timeout}s")
    finally:
        script.unload()
        session.detach()

    if result.get("event") != "map_entities" or entity_bytes is None:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    raw_entity_bytes = entity_bytes.rstrip(b"\0")
    text = raw_entity_bytes.decode("utf-8", errors="replace")
    entities = parse_entities(text)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw_entity_bytes)
    summary = {
        **result,
        "pid": pid,
        "entity_count": len(entities),
        "spawn_candidates": spawn_candidates(entities),
        "output": str(args.output.resolve()) if args.output is not None else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
