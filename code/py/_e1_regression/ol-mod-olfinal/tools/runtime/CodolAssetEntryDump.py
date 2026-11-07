#!/usr/bin/env python3
"""READ-ONLY enumeration of a running client's XAsset entry table.

Calls nothing. DB_LinkXAssetEntry (sub_49DA10) walks this table itself, and its
disassembly gives the layout outright:

    entries at 0x239B120, 28-byte stride
      +0  u32 type          +8  header pointer
      +16 u8  (default?)    +17 u8 flags        +20 u32 next   +24 u32 alt-next

so the whole table can be read without touching DB_FindXAssetHeader - which
blocks on a streaming event and branches on the calling thread id, and is
therefore not safe to call from an arbitrary thread.

The name lives at a per-type offset inside the header. Only the types this port
needs are decoded:

    2  XAnimParts  name at +0     4  XModel    name at +0
    5  Material    name at +16   10  GfxImage  name at +48

Written to answer two questions at once: did the animations this session
published actually land in the table, and which shipped Materials exist to clone
from - the choice a Material port cannot be built without.
"""
import sys
import json
import argparse
from collections import Counter

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


AGENT = r"""
'use strict';
const ENTRIES = ptr(0x239B120);
const STRIDE = 28;
// name offset inside the header, by asset type
const NAME_AT = { 2: 0, 4: 0, 5: 16, 10: 48 };

function readName(type, header) {
    const off = NAME_AT[type];
    if (off === undefined) return null;
    try {
        const p = header.add(off).readPointer();
        if (p.isNull()) return null;
        // Read to the NUL by hand. readCString does not reliably stop at it here,
        // and running past the terminator drags the next array into the name -
        // which silently failed every printable check and hid 3,263 assets.
        let s = '';
        for (let i = 0; i < 96; i++) {
            const c = p.add(i).readU8();
            if (c === 0) return s.length === 0 ? null : s;
            if (c < 32 || c > 126) return null;
            s += String.fromCharCode(c);
        }
        return null;
    } catch (e) { return null; }
}

rpc.exports.dump = function (wantTypes, match, limit) {
    const out = { counts: {}, hits: [], scanned: 0, materialSlots: {} };
    const want = new Set(wantTypes);
    for (let i = 1; i < 200000; i++) {
        const e = ENTRIES.add(STRIDE * i);
        let type, header;
        try { type = e.readU32(); header = e.add(8).readPointer(); }
        catch (err) { out.stoppedAt = i; break; }
        if (type > 64 || header.isNull()) continue;
        out.scanned = i;
        out.counts[type] = (out.counts[type] || 0) + 1;
        if (!want.has(type)) continue;
        const name = readName(type, header);
        if (name === null) continue;
        if (match !== '' && name.indexOf(match) < 0) continue;
        if (out.hits.length >= limit) continue;
        const hit = { index: i, type: type, name: name, header: header.toString() };
        if (type === 5) {
            try {
                const tc = header.add(81).readU8();
                hit.textureCount = tc;
                const table = header.add(92).readPointer();
                hit.slots = [];
                for (let k = 0; k < tc && k < 8; k++) {
                    hit.slots.push('0x' + table.add(12 * k).readU32().toString(16));
                }
                out.materialSlots[hit.slots.join(',')] =
                    (out.materialSlots[hit.slots.join(',')] || 0) + 1;
            } catch (err) {}
        }
        out.hits.push(hit);
    }
    return out;
};
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", default="5", help="comma-separated asset types")
    ap.add_argument("--match", default="", help="substring the name must contain")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--pid", type=int)
    a = ap.parse_args()

    types = [int(t) for t in a.types.split(",") if t]
    device = frida.get_local_device()
    procs = [q for q in device.enumerate_processes() if q.name.lower() == "out.exe"]
    pid = a.pid or (procs[0].pid if procs else None)
    if pid is None:
        print("no client process found")
        return 2
    print("clients:", [(p.pid, p.name) for p in procs], "-> using", pid)

    session = device.attach(pid)
    script = session.create_script(AGENT)
    script.load()
    r = script.exports_sync.dump(types, a.match, a.limit)

    print("entries scanned: %s" % r["scanned"])
    counts = {int(k): v for k, v in r["counts"].items()}
    print("entries by type (top 12):",
          dict(Counter(counts).most_common(12)))
    print()
    for hit in r["hits"]:
        extra = ""
        if hit.get("slots"):
            extra = "  %d slots [%s]" % (hit["textureCount"], ", ".join(hit["slots"]))
        print("  type %-3d %-52s %s%s" % (hit["type"], hit["name"], hit["header"], extra))
    if r.get("materialSlots"):
        print()
        print("material slot signatures seen:")
        for sig, n in sorted(r["materialSlots"].items(), key=lambda kv: -kv[1])[:10]:
            print("   %-44s x%d" % (sig, n))
    session.detach()
    return 0


if __name__ == "__main__":
    sys.exit(main())
