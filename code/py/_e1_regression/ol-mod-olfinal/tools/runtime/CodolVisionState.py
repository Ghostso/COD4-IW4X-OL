#!/usr/bin/env python3
r"""Read a running CODOL client's vision-set state. Read-only, client pids only.

WHAT IT READS, and why these addresses.

out.exe's client server-command dispatcher (0x00613A40) switches on the verb
CHARACTER and six of its cases are the vision family. Every one of them computes
the same obfuscated base first:

    esi = dword_1C1D188[dword_82C3B58] ^ 0xFBB2C97A          (0x613a84..0x613a94)

then copies argv(1) into a 0x40-byte NAME buffer at a fixed displacement off
that base, reads argv(2) with atoi as a blend time in milliseconds, and calls
the applier at 0x0046CEF0 with a vision TYPE index:

    'N' 78 -> type 0   +0x192578      <- the map grade, what this tool is for
    'O' 79 -> type 1   +0x1925B8
    'P' 80 -> type 2   +0x1925F8
    'Q' 81 -> type 3   +0x192638
    'R' 82 -> type 4   +0x192678
    '3' 51 -> type 5   +0x1926B8

The applier writes a 20-byte STATE record per type off the same base, and it
writes it ONLY after DB_FindXAssetHeader returns the asset, so the state is the
oracle for "did the vision set actually load", not just "was the command heard":

    0x0046CE80   state = 1, fraction = 1.0, time = now       instant
    0x0046CEF0   state = 3, duration, start time             blending
    neither ran / the asset was not found                    state stays 0

    state[type] = base + 4 * (5 * type + 411970) = base + 0x192508 + 20 * type

MEASURED, and it is why this tool hexdumps: type 0's state really is at
+0x192508 and its record reads {1, 1.0f, 156157} against name "mp_rust_long" at
+0x192578.

THE STRIDE IS NOW CONFIRMED FOR ALL SIX TYPES, and the old doubt was an
off-by-eight in the reading rather than in the stride. The worry was that 20
bytes would run type 5's record into the name array. It does not: +0x192508 is
not the START of an entry, it is entry+8. Both appliers write four fields around
it -- 0x0046CE80 writes +12 and +16, 0x0046CEF0 writes +0 and +4 -- so an entry
runs [entry, entry+20) with STATE at entry+8:

    +0    blend start time        0x0046CEF0
    +4    blend duration          0x0046CEF0
    +8    STATE                   1 = applied instantly, 3 = blending, 0 = never set
    +12   float 1.0               0x0046CE80
    +16   time                    0x0046CE80

Laying the whole region out from the appliers' own expressions closes it, with
no gaps and no overlaps across four arrays and three different strides:

    0x191A98 .. 0x191E10   6 x 148   blend FROM   (qmemcpy target in 0x0046CEF0)
    0x191E10 .. 0x192188   6 x 148   blend TO
    0x192188 .. 0x192500   6 x 148   current      (sub_46C660 fills this one)
    0x192500 .. 0x192578   6 x  20   state entries, STATE at +8
    0x192578 .. 0x1926F8   6 x 0x40  name buffers

Four arrays butting exactly, all six entries wide. That is the struct, and it is
independent confirmation that there are exactly SIX vision types. Type 5's state
is at +0x19256C and is as readable as type 0's.

So a client that was never told carries name "" and state 0, and the engine
renders vision/default.vision -- the flat, ungraded look. A client that was told
carries the map name and state 1.
"""

from __future__ import annotations

import argparse
import json
import sys

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


MODULE_NAME = "out.exe"
IMAGE_BASE = 0x400000

# The two globals the base is built from, and the constant it is masked with.
RVA_INDEX = 0x82C3B58 - IMAGE_BASE       # dword_82C3B58, the slot selector
RVA_TABLE = 0x1C1D188 - IMAGE_BASE       # dword_1C1D188, the pointer table
BASE_MASK = 0xFBB2C97A

# Displacements off the resolved base.
STATE_ZERO = 0x192508                    # 4 * 411970, and measured in a live client
STATE_STRIDE = 20
NAME_ZERO = 0x192578
NAME_STRIDE = 0x40
NAME_BYTES = 0x40

TYPE_NAMES = ("naked", "night", "missilecam", "thermal", "pain", "type5")
TYPE_VERBS = ("N", "O", "P", "Q", "R", "3")

AGENT_SOURCE = r"""
'use strict';

rpc.exports.read = function (config) {
    const module = Process.findModuleByName(config.moduleName);
    if (module === null)
        return { error: 'module ' + config.moduleName + ' is not loaded' };

    const index = module.base.add(config.rvaIndex).readU32();
    const slot = module.base.add(config.rvaTable).add(index * 4).readU32();
    const base = slot ^ config.baseMask;
    if (base === 0 || slot === 0)
        return { error: 'the vision base is not built yet', slot: slot, index: index };

    const basePointer = ptr(base >>> 0);
    const entries = [];
    for (let type = 0; type < config.typeCount; type += 1) {
        const statePointer = basePointer.add(config.stateZero + config.stateStride * type);
        const namePointer = basePointer.add(config.nameZero + config.nameStride * type);
        let state = null;
        let fraction = null;
        let name = null;
        try { state = statePointer.readU32(); } catch (error) { state = null; }
        try { fraction = statePointer.add(4).readFloat(); } catch (error) { fraction = null; }
        try {
            // The buffer is 0x40 raw bytes and an unset one holds whatever was
            // there before, so keep only printable ASCII up to the NUL rather
            // than handing the host a decode problem.
            const raw = namePointer.readByteArray(config.nameBytes);
            const bytes = new Uint8Array(raw);
            let text = '';
            for (let at = 0; at < bytes.length; at += 1) {
                const value = bytes[at];
                if (value === 0) break;
                text += (value >= 0x20 && value < 0x7f)
                    ? String.fromCharCode(value)
                    : '?';
            }
            name = text;
        } catch (error) { name = null; }
        entries.push({ type: type, state: state, fraction: fraction, name: name });
    }
    let dump = null;
    if (config.dumpFrom !== 0) {
        try {
            const raw = basePointer.add(config.dumpFrom).readByteArray(config.dumpBytes);
            dump = Array.from(new Uint8Array(raw));
        } catch (error) { dump = null; }
    }
    return {
        moduleBase: module.base.toString(),
        base: basePointer.toString(),
        entries: entries,
        dump: dump,
        dumpFrom: config.dumpFrom,
    };
};
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True,
                        help="a CLIENT process id -- never the dedicated one")
    parser.add_argument("--module", default=MODULE_NAME)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dump-from", type=lambda v: int(v, 0), default=0,
                        help="displacement off the vision base to hexdump")
    parser.add_argument("--dump-bytes", type=lambda v: int(v, 0), default=0x200)
    arguments = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    session = frida.attach(arguments.pid)
    try:
        script = session.create_script(AGENT_SOURCE)
        script.load()
        result = script.exports_sync.read({
            "moduleName": arguments.module,
            "rvaIndex": RVA_INDEX,
            "rvaTable": RVA_TABLE,
            "baseMask": BASE_MASK,
            "stateZero": STATE_ZERO,
            "stateStride": STATE_STRIDE,
            "nameZero": NAME_ZERO,
            "nameStride": NAME_STRIDE,
            "nameBytes": NAME_BYTES,
            "typeCount": len(TYPE_NAMES),
            "dumpFrom": arguments.dump_from,
            "dumpBytes": arguments.dump_bytes,
        })
    finally:
        session.detach()

    if arguments.json:
        print(json.dumps(result, indent=2))
        return 0 if "error" not in result else 1

    if "error" in result:
        print("FAILED: " + str(result["error"]))
        return 1

    print("module base " + result["moduleBase"] + "  vision base " + result["base"])
    applied = False
    for entry in result["entries"]:
        index = entry["type"]
        state = entry["state"]
        meaning = {0: "NOT SET (engine renders vision/default.vision)",
                   1: "applied", 3: "blending"}.get(state, "state " + str(state))
        name = entry["name"] or ""
        print("  %-10s verb '%s'  state=%-2s %-42s name=%r"
              % (TYPE_NAMES[index], TYPE_VERBS[index],
                 "?" if state is None else state, meaning, name))
        if index == 0 and state in (1, 3) and name:
            applied = True
    if result.get("dump"):
        data = bytes(result["dump"])
        start = result["dumpFrom"]
        for at in range(0, len(data), 16):
            row = data[at:at + 16]
            text = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in row)
            print("  +%06X  %-47s |%s|"
                  % (start + at, " ".join("%02X" % b for b in row), text))
    print("naked vision set: " + ("APPLIED" if applied else "NOT APPLIED"))
    return 0 if applied else 1


if __name__ == "__main__":
    sys.exit(main())
