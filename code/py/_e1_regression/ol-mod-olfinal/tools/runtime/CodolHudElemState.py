#!/usr/bin/env python3
"""Read the native CODOL snapshot HudElem active prefixes without mutation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from CodolFridaRuntime import configure_frida_runtime


configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
ENCODED_CGAME_GLOBALS_RVA = 0x1619510
ACTIVE_LOCAL_CLIENT_INDEX_RVA = 0x7417BA8
CGAME_POINTER_XOR = 0xFBB2C97A
HUDELEM_FIELDS_RVA = 0x856AC0
SNAPSHOT_POINTER_OFFSET = 0x3578
HUDELEM_CURRENT_OFFSET = 0xA78
HUDELEM_ARCHIVAL_OFFSET = 0x1ED0
HUDELEM_SIZE = 0xA8
HUDELEM_COUNT = 31
HUDELEM_FIELD_COUNT = 42
SELECTED_FIELDS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 14)


def build_script() -> str:
    return f"""
'use strict';

const module = Process.getModuleByName({json.dumps(TARGET_NAME)});
const encodedCgameGlobals = module.base.add({ENCODED_CGAME_GLOBALS_RVA});
const activeLocalClientIndex = module.base.add({ACTIVE_LOCAL_CLIENT_INDEX_RVA});
const hudelemFields = module.base.add({HUDELEM_FIELDS_RVA});
const selectedFields = {json.dumps(SELECTED_FIELDS)};

function readableU32(address) {{
    try {{ return address.readU32(); }} catch (_) {{ return null; }}
}}

function readableS32(address) {{
    try {{ return address.readS32(); }} catch (_) {{ return null; }}
}}

function readableFloat(address) {{
    try {{ return address.readFloat(); }} catch (_) {{ return null; }}
}}

function readablePointer(address) {{
    try {{
        const value = address.readPointer();
        return value.isNull() ? null : value;
    }} catch (_) {{
        return null;
    }}
}}

function currentCgame() {{
    const clientIndex = readableU32(activeLocalClientIndex);
    if (clientIndex === null || clientIndex > 15) return null;
    const encoded = readableU32(encodedCgameGlobals.add(clientIndex * 4));
    if (encoded === null) return null;
    const cgame = ptr((encoded ^ {CGAME_POINTER_XOR}) >>> 0);
    return readableU32(cgame) === null ? null : cgame;
}}

function readDescriptor(index) {{
    const entry = hudelemFields.add(index * 12);
    return {{
        index: index,
        offset: readableU32(entry),
        bits: readableS32(entry.add(4)),
        change_hint: readableU32(entry.add(8))
    }};
}}

function readArray(playerState, baseOffset, descriptors) {{
    const result = [];
    for (let index = 0; index < {HUDELEM_COUNT}; ++index) {{
        const entry = playerState.add(baseOffset + index * {HUDELEM_SIZE});
        const type = readableS32(entry);
        if (type === null || type === 0) break;
        const fields = selectedFields.map(function(fieldIndex) {{
            const descriptor = descriptors[fieldIndex];
            const address = entry.add(descriptor.offset);
            return {{
                index: fieldIndex,
                offset: descriptor.offset,
                bits: descriptor.bits,
                raw_u32: readableU32(address),
                float: readableFloat(address)
            }};
        }});
        result.push({{ index: index, type: type, fields: fields }});
    }}
    return result;
}}

rpc.exports = {{
    capture() {{
        const cgame = currentCgame();
        if (cgame === null) return {{ ok: false, error: 'cgame unavailable' }};
        const snapshot = readablePointer(cgame.add({SNAPSHOT_POINTER_OFFSET}));
        if (snapshot === null) return {{ ok: false, error: 'snapshot unavailable' }};
        const descriptors = [];
        for (let index = 0; index < {HUDELEM_FIELD_COUNT}; ++index)
            descriptors.push(readDescriptor(index));
        if (descriptors.some(function(field) {{ return field.offset === null; }}))
            return {{ ok: false, error: 'hudelem descriptor unavailable' }};
        return {{
            ok: true,
            pid: Process.id,
            module_base: module.base.toString(),
            snapshot: snapshot.toString(),
            current: readArray(snapshot, {HUDELEM_CURRENT_OFFSET}, descriptors),
            archival: readArray(snapshot, {HUDELEM_ARCHIVAL_OFFSET}, descriptors)
        }};
    }}
}};
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    device = frida.get_local_device()
    session = device.attach(args.pid)
    try:
        script = session.create_script(build_script())
        script.load()
        result = script.exports_sync.capture()
    finally:
        session.detach()
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
