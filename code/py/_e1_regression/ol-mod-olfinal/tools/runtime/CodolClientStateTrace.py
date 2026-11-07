#!/usr/bin/env python3
"""Read the clientState_s rows produced by CODOL's packet-client parser."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from CodolFridaRuntime import configure_frida_runtime


configure_frida_runtime()
import frida


TARGET_NAME = "codoMP_client_shipRetail.exe"
CL_PARSE_PACKET_CLIENTS_RVA = 0x06CC60
MSG_READ_DELTA_FIELD_RVA = 0x1A27F0
CLIENT_STATE_NETFIELDS_RVA = 0x854298
CLIENT_STATE_SIZE = 0x58
CLIENT_STATE_RING_XOR = 0x3613BDA3


def build_script() -> str:
    return f"""
'use strict';

const module = Process.getModuleByName({json.dumps(TARGET_NAME)});
const stateSize = {CLIENT_STATE_SIZE};
const clientStateFields = module.base.add({CLIENT_STATE_NETFIELDS_RVA});
const observations = {{}};
let parseCount = 0;
let teamFieldReadCount = 0;
let lastTeamFieldRead = null;
let last = null;

function readU32(address) {{ try {{ return address.readU32(); }} catch (_) {{ return null; }} }}
function readU16(address) {{ try {{ return address.readU16(); }} catch (_) {{ return null; }} }}
function readU8(address) {{ try {{ return address.readU8(); }} catch (_) {{ return null; }} }}

function readRows(snapshot, clientActive) {{
    const count = readU32(snapshot.add(0x3548));
    const first = readU32(snapshot.add(0x3558));
    const encodedRing = readU32(clientActive.add(8611 * 4));
    const capacity = readU32(clientActive.add(8605 * 4));
    if (count === null || first === null || encodedRing === null ||
        capacity === null || capacity === 0 || capacity > 4096 || count > capacity) {{
        return {{ count, first, capacity, rows: [], error: 'invalid packet-client ring metadata' }};
    }}
    const ring = ptr((encodedRing ^ {CLIENT_STATE_RING_XOR}) >>> 0);
    const rows = [];
    for (let i = 0; i < count; ++i) {{
        const row = ring.add(((first + i) % capacity) * stateSize);
        const item = {{
            address: row.toString(),
            client_num: readU32(row),
            model_index_candidate: readU32(row.add(4)),
            team: readU32(row.add(8)),
            attachment_0_candidate: readU16(row.add(12)),
            attachment_tag_0_candidate: readU16(row.add(20)),
            weapon_0_candidate: readU16(row.add(52)),
            raw_hex: Array.from(new Uint8Array(row.readByteArray(stateSize)))
                .map(value => value.toString(16).padStart(2, '0')).join('')
        }};
        rows.push(item);
        const key = `${{item.client_num}}:${{item.team}}:${{item.model_index_candidate}}`;
        observations[key] = (observations[key] || 0) + 1;
    }}
    return {{ count, first, capacity, ring: ring.toString(), rows }};
}}

Interceptor.attach(module.base.add({CL_PARSE_PACKET_CLIENTS_RVA}), {{
    onEnter(args) {{
        // Native signature is x86 fastcall: snapshot in ECX, msg in EDX,
        // followed by clientActive, serverMessageSequence, oldSnapshot.
        this.snapshot = this.context.ecx;
        this.clientActive = args[0];
    }},
    onLeave() {{
        parseCount += 1;
        last = readRows(this.snapshot, this.clientActive);
    }}
}});

Interceptor.attach(module.base.add({MSG_READ_DELTA_FIELD_RVA}), {{
    onEnter() {{
        this.isClientTeam = this.context.ecx.equals(clientStateFields.add(21 * 12));
        if (!this.isClientTeam) return;
        this.destination = this.context.edx.add(8);
        this.before = readU32(this.destination);
    }},
    onLeave() {{
        if (!this.isClientTeam) return;
        teamFieldReadCount += 1;
        lastTeamFieldRead = {{
            before: this.before,
            after: readU32(this.destination)
        }};
    }}
}});

rpc.exports = {{
    capture() {{
        return {{
            ok: true,
            pid: Process.id,
            module_base: module.base.toString(),
            parse_count: parseCount,
            team_field_read_count: teamFieldReadCount,
            last_team_field_read: lastTeamFieldRead,
            observations: {{ ...observations }},
            last
        }};
    }}
}};
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")

    session = frida.get_local_device().attach(args.pid)
    try:
        script = session.create_script(build_script())
        script.load()
        time.sleep(args.seconds)
        result = script.exports_sync.capture()
    finally:
        session.detach()

    output = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if result.get("ok") and result.get("parse_count", 0) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
