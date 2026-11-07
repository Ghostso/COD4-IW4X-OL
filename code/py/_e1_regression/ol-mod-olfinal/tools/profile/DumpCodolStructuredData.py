#!/usr/bin/env python3
"""Dump CODOL StructuredDataDefSet assets and resolve Publicprofile offsets."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
PROFILE_DDL_BASE = 4

AGENT_SOURCE = r"""
'use strict';

if (Process.pointerSize !== 4) throw new Error('CODOL StructuredData dumper requires a 32-bit target');
const module = Process.getModuleByName('codoMP_client_shipRetail.exe');
// CODOL extends IW4's 52-byte definition with offsetMapCount/offsetMap.
const STRUCTURED_DATA_DEF_SIZE = 60;
const DB_FindXAssetHeader = new NativeFunction(
    module.base.add(0x9E7D0),
    'pointer',
    ['int', 'pointer', 'int']
);

function checkedCount(value, maximum, label) {
    if (value < 0 || value > maximum) throw new Error('invalid ' + label + ': ' + value);
    return value;
}

function stringAt(address) {
    return address.isNull() ? null : address.readCString();
}

function scriptStringRef(address) {
    const value = address.readU32();
    let text = null;
    if (value >= 0x10000) {
        try { text = ptr(value).readCString(); } catch (_) { text = null; }
    }
    return { id: value, text: text };
}

function dataType(address) {
    return { category: address.readS32(), index_or_length: address.add(4).readS32() };
}

function dumpEnums(definition) {
    const count = checkedCount(definition.add(8).readS32(), 10000, 'enum count');
    const base = definition.add(12).readPointer();
    const result = [];
    for (let index = 0; index < count; ++index) {
        const item = base.add(index * 12);
        const entryCount = checkedCount(item.readS32(), 100000, 'enum entry count');
        const entries = item.add(8).readPointer();
        const values = [];
        for (let entryIndex = 0; entryIndex < entryCount; ++entryIndex) {
            const entry = entries.add(entryIndex * 8);
            values.push({ name: scriptStringRef(entry), index: entry.add(4).readU16() });
        }
        result.push({
            entry_count: entryCount,
            reserved_entry_count: item.add(4).readS32(),
            entries: values
        });
    }
    return result;
}

function dumpStructs(definition) {
    const count = checkedCount(definition.add(16).readS32(), 10000, 'struct count');
    const base = definition.add(20).readPointer();
    const result = [];
    for (let index = 0; index < count; ++index) {
        const item = base.add(index * 20);
        const propertyCount = checkedCount(item.readS32(), 100000, 'property count');
        const properties = item.add(4).readPointer();
        const values = [];
        for (let propertyIndex = 0; propertyIndex < propertyCount; ++propertyIndex) {
            const property = properties.add(propertyIndex * 24);
            values.push({
                name: scriptStringRef(property),
                type: dataType(property.add(4)),
                offset: property.add(12).readU32(),
                flags: property.add(16).readU32(),
                extra: property.add(20).readU32()
            });
        }
        result.push({
            property_count: propertyCount,
            size: item.add(8).readU32(),
            unknown_0c: item.add(12).readU32(),
            logical_stride: item.add(16).readU32(),
            properties: values
        });
    }
    return result;
}

function dumpArrays(definition, countOffset, pointerOffset, label) {
    const count = checkedCount(definition.add(countOffset).readS32(), 10000, label + ' count');
    const base = definition.add(pointerOffset).readPointer();
    const result = [];
    for (let index = 0; index < count; ++index) {
        const item = base.add(index * 16);
        result.push({
            count_or_enum_index: item.readS32(),
            element_type: dataType(item.add(4)),
            element_size: item.add(12).readU32()
        });
    }
    return result;
}

function dumpDefinition(definition) {
    const offsetCount = checkedCount(definition.add(52).readS32(), 1000000, 'offset map count');
    const offsetBase = definition.add(56).readPointer();
    const offsetMap = [];
    for (let index = 0; index < offsetCount; ++index) offsetMap.push(offsetBase.add(index * 4).readU32());
    return {
        version: definition.readS32(),
        format_checksum: definition.add(4).readU32(),
        enums: dumpEnums(definition),
        structs: dumpStructs(definition),
        indexed_arrays: dumpArrays(definition, 24, 28, 'indexed array'),
        enumed_arrays: dumpArrays(definition, 32, 36, 'enumed array'),
        root_type: dataType(definition.add(40)),
        size: definition.add(48).readU32(),
        offset_map: offsetMap
    };
}

rpc.exports = {
    probe(name) {
        const set = DB_FindXAssetHeader(39, Memory.allocUtf8String(name), 1);
        if (set.isNull()) throw new Error('StructuredDataDefSet not found: ' + name);
        const definitions = set.add(8).readPointer();
        const words = [];
        for (let index = 0; index < 24; ++index) words.push(definitions.add(index * 4).readU32());
        return {
            set_address: set.toString(),
            set_name_pointer: set.readPointer().toString(),
            set_name: stringAt(set.readPointer()),
            definition_count: set.add(4).readS32(),
            definitions_address: definitions.toString(),
            first_definition_words: words
        };
    },
    dump(name) {
        const set = DB_FindXAssetHeader(39, Memory.allocUtf8String(name), 1);
        if (set.isNull()) throw new Error('StructuredDataDefSet not found: ' + name);
        const count = checkedCount(set.add(4).readS32(), 1000, 'definition count');
        const definitions = set.add(8).readPointer();
        const result = [];
        for (let index = 0; index < count; ++index) {
            result.push(dumpDefinition(definitions.add(index * STRUCTURED_DATA_DEF_SIZE)));
        }
        return { name: stringAt(set.readPointer()), definition_count: count, definitions: result };
    }
};
"""


TYPE_NAMES = {
    0: "int",
    1: "byte",
    2: "bool",
    3: "string",
    4: "enum",
    5: "struct",
    6: "indexed_array",
    7: "enum_array",
    8: "float",
    9: "short",
}


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help=f"Defaults to the newest {TARGET_NAME}")
    parser.add_argument("--asset", action="append", dest="assets")
    parser.add_argument(
        "--profile-offset",
        action="append",
        type=parse_int,
        default=[],
        help="Decoded Publicprofile byte offset to resolve, such as 0x111D",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--probe-only", action="store_true")
    parser.set_defaults(repository=repository)
    return parser.parse_args()


def find_pid(device: frida.core.Device) -> int | None:
    matches = [process for process in device.enumerate_processes() if process.name.lower() == TARGET_NAME.lower()]
    return max(matches, key=lambda process: process.pid).pid if matches else None


def primitive_size(type_info: dict[str, int]) -> int:
    category = type_info["category"]
    if category in (0, 8):
        return 4
    if category in (1, 2):
        return 1
    if category == 3:
        return max(0, type_info["index_or_length"])
    if category in (4, 9):
        return 2
    return 0


def resolve_offset(
    definition: dict[str, Any],
    type_info: dict[str, int],
    target: int,
    logical_base: int = 0,
    path: str = "root",
    depth: int = 0,
) -> list[dict[str, Any]]:
    if depth > 64:
        return []
    category = type_info["category"]
    index = type_info["index_or_length"]
    type_name = TYPE_NAMES.get(category, f"unknown_{category}")
    if category == 2:
        offset_map = definition["offset_map"]
        if not 0 <= logical_base < len(offset_map):
            return []
        bit_offset = offset_map[logical_base]
        actual_base = bit_offset >> 3
        if actual_base == target:
            bit_index = bit_offset & 7
            return [{
                "path": path,
                "type": type_name,
                "offset": actual_base,
                "logical_offset": logical_base,
                "size": 1,
                "bit_offset": bit_offset,
                "bit_index": bit_index,
                "bit_mask": 1 << bit_index,
            }]
        return []
    size = primitive_size(type_info)
    if size:
        offset_map = definition["offset_map"]
        if 0 <= logical_base < len(offset_map):
            actual_base = offset_map[logical_base]
        else:
            return []
        if actual_base <= target < actual_base + size:
            return [{
                "path": path,
                "type": type_name,
                "offset": actual_base,
                "logical_offset": logical_base,
                "size": size,
            }]
        return []

    results: list[dict[str, Any]] = []
    if category == 5 and 0 <= index < len(definition["structs"]):
        struct = definition["structs"][index]
        for property_info in struct["properties"]:
            results.extend(
                resolve_offset(
                    definition,
                    property_info["type"],
                    target,
                    logical_base + property_info["offset"],
                    f"{path}.{property_info['name'].get('text') or '#' + str(property_info['name']['id'])}",
                    depth + 1,
                )
            )
    elif category == 6 and 0 <= index < len(definition["indexed_arrays"]):
        array = definition["indexed_arrays"][index]
        count = array["count_or_enum_index"]
        element_type = array["element_type"]
        element_category = element_type["category"]
        element_type_index = element_type["index_or_length"]
        logical_stride = 1
        if element_category == 5 and 0 <= element_type_index < len(definition["structs"]):
            logical_stride = definition["structs"][element_type_index]["logical_stride"]
        if logical_stride > 0:
            for element_index in range(count):
                results.extend(
                    resolve_offset(
                        definition,
                        element_type,
                        target,
                        logical_base + element_index * logical_stride,
                        f"{path}[{element_index}]",
                        depth + 1,
                    )
                )
    elif category == 7 and 0 <= index < len(definition["enumed_arrays"]):
        array = definition["enumed_arrays"][index]
        enum_index = array["count_or_enum_index"]
        if 0 <= enum_index < len(definition["enums"]):
            enum = definition["enums"][enum_index]
            count = enum["entry_count"]
            for element_index in range(count):
                entry_name = next(
                    (
                        item["name"].get("text") or f"#{item['name']['id']}"
                        for item in enum["entries"]
                        if item["index"] == element_index
                    ),
                    str(element_index),
                )
                results.extend(
                    resolve_offset(
                        definition,
                        array["element_type"],
                        target,
                        logical_base + element_index,
                        f"{path}[{entry_name}]",
                        depth + 1,
                    )
                )
    return results


def add_resolutions(asset: dict[str, Any], profile_offsets: list[int]) -> None:
    for definition in asset["definitions"]:
        resolutions = []
        for profile_offset in profile_offsets:
            ddl_offset = profile_offset - PROFILE_DDL_BASE
            resolutions.append(
                {
                    "profile_offset": profile_offset,
                    "ddl_offset": ddl_offset,
                    "matches": resolve_offset(definition, definition["root_type"], ddl_offset),
                }
            )
        definition["resolved_offsets"] = resolutions


def main() -> int:
    args = parse_args()
    device = frida.get_local_device()
    pid = args.pid or find_pid(device)
    if pid is None:
        print(f"No running {TARGET_NAME} was found.", file=sys.stderr)
        return 2

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (args.output_dir or args.repository / "diagnostics" / "structured_data" / stamp).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    session = device.attach(pid)
    script = session.create_script(AGENT_SOURCE)
    errors: list[str] = []
    script.on("message", lambda message, _data: errors.append(str(message)) if message.get("type") == "error" else None)
    script.load()
    try:
        for name in args.assets or ["mp/playerdata.def", "mp/playersecuredata.def"]:
            if args.probe_only:
                probe = script.exports_sync.probe(name)
                filename = name.replace("/", "_").replace("\\", "_") + ".probe.json"
                (output_dir / filename).write_text(json.dumps(probe, indent=2), encoding="utf-8")
                print(json.dumps(probe, indent=2))
                continue
            asset = script.exports_sync.dump(name)
            add_resolutions(asset, args.profile_offset)
            filename = name.replace("/", "_").replace("\\", "_") + ".json"
            (output_dir / filename).write_text(json.dumps(asset, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"{name}: {asset['definition_count']} definitions")
            for definition in asset["definitions"]:
                print(
                    f"  version={definition['version']} checksum=0x{definition['format_checksum']:08X} "
                    f"size={definition['size']}"
                )
                for resolution in definition["resolved_offsets"]:
                    paths = ", ".join(item["path"] for item in resolution["matches"]) or "<unresolved>"
                    print(
                        f"    profile 0x{resolution['profile_offset']:04X} / "
                        f"DDL 0x{resolution['ddl_offset']:04X}: {paths}"
                    )
    finally:
        script.unload()
        session.detach()

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Dumped StructuredData assets to: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
