#!/usr/bin/env python3
"""READ-ONLY verification of the XAsset hash lookup, against every asset a client
holds.

`DB_FindXAssetHeader` (0x49CF30) is the wrong door for anything driven from
outside: it takes a critical section, waits on a streaming event, and branches on
GetCurrentThreadId three separate ways. But ALL of that is its wrapper. The
lookup itself is `sub_49CA70`, and it is pure:

    bucket = sub_49C870(type, name)
    for (i = heads[bucket]; i; i = entry[i].next)
        if (entry[i].type == type && case-insensitive equal(name, nameOf(entry[i])))
            return entry[i]

    entries  dword_239B120   28-byte stride   +0 type  +8 header  +20 next
    heads    dword_1E2D338   one u32 per bucket
    buckets  0x1D4C0 = 120,000

and the hash, `sub_49C870`, is seeded with the ASSET TYPE - `mov eax, edi` at
0x49DA60, where edi holds it:

    h = type
    for each char:  c = tolower(ch);  h = 31*h + (c == '\\' ? '/' : c)
    return h % 120000

The name's offset inside a header is not guesswork either. `funcs_49CACE` at
0xE5C8C0 is the engine's own per-type accessor table:

    funcs[0..4]  0x483390   **(DWORD **)p        -> name at header +0
    funcs[5]     0x4833A0   *(DWORD *)(*p + 16)  -> Material at +16
    funcs[10]    0x4833C0   *(DWORD *)(*p + 48)  -> GfxImage at +48

THE CHECK. Rather than test a handful of names, this walks all 120,000 buckets,
and for every entry in every chain recomputes the hash from that entry's own name
and requires it to equal the bucket the entry was found in. An asset whose hash
does not reproduce its bucket is an asset this lookup would never find, so the
only acceptable result is all of them.
"""
import sys
import argparse
from collections import Counter

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


AGENT = r"""
'use strict';
const ENTRIES = ptr(0x239B120);
const HEADS   = ptr(0x1E2D338);
const STRIDE  = 28;
const BUCKETS = 0x1D4C0;

// funcs_49CACE at 0xE5C8C0: 0x483390 -> +0, 0x4833A0 -> +16, 0x4833C0 -> +48.
function nameOffsetFor(type) {
    try {
        const fn = ptr(0xE5C8C0).add(4 * type).readPointer().toUInt32();
        if (fn === 0x483390) return 0;
        if (fn === 0x4833A0) return 16;
        if (fn === 0x4833C0) return 48;
        return -1;
    } catch (e) { return -1; }
}

function readName(header, off) {
    try {
        const p = header.add(off).readPointer();
        if (p.isNull()) return null;
        let s = '';
        for (let i = 0; i < 256; i++) {
            const c = p.add(i).readU8();
            if (c === 0) return s;
            s += String.fromCharCode(c);
        }
        return null;
    } catch (e) { return null; }
}

function hash(type, name) {
    let h = type >>> 0;
    for (let i = 0; i < name.length; i++) {
        let c = name.charCodeAt(i);
        if (c >= 65 && c <= 90) c += 32;          // tolower
        if (c === 92) c = 47;                      // backslash normalises to slash
        h = (Math.imul(31, h) + c) >>> 0;
    }
    return h % 0x1D4C0;
}

rpc.exports.verify = function (sampleLimit) {
    const out = {
        buckets: BUCKETS, chains: 0, entries: 0, exact: 0,
        unreadableName: 0, unknownType: 0, byType: {}, mismatches: [],
        longestChain: 0, samples: [],
    };
    const offsets = {};

    for (let b = 0; b < BUCKETS; b++) {
        let i;
        try { i = HEADS.add(4 * b).readU32(); } catch (e) { break; }
        if (i === 0) continue;
        out.chains++;
        let depth = 0;
        while (i !== 0 && depth < 4096) {
            depth++;
            const e = ENTRIES.add(STRIDE * i);
            let type, header, next;
            try {
                type = e.readU32();
                header = e.add(8).readPointer();
                next = e.add(20).readU32();
            } catch (err) { break; }
            out.entries++;
            out.byType[type] = (out.byType[type] || 0) + 1;

            if (!(type in offsets)) offsets[type] = nameOffsetFor(type);
            const off = offsets[type];
            if (off < 0) { out.unknownType++; i = next; continue; }
            const name = header.isNull() ? null : readName(header, off);
            if (name === null) { out.unreadableName++; i = next; continue; }

            const h = hash(type, name);
            if (h === b) {
                out.exact++;
                if (out.samples.length < sampleLimit &&
                    (type === 2 || type === 4 || type === 5 || type === 10)) {
                    out.samples.push({ type: type, name: name, bucket: b,
                                       header: header.toString() });
                }
            } else if (out.mismatches.length < 12) {
                out.mismatches.push({ type: type, name: name, bucket: b, hashed: h });
            }
            i = next;
        }
        if (depth > out.longestChain) out.longestChain = depth;
    }
    out.nameOffsets = offsets;
    return out;
};

// The lookup itself, exactly as sub_49CA70 walks it.
rpc.exports.find = function (type, name) {
    const off = nameOffsetFor(type);
    if (off < 0) return { error: 'no name accessor for type ' + type };
    const b = hash(type, name);
    let i;
    try { i = HEADS.add(4 * b).readU32(); } catch (e) { return { error: '' + e }; }
    let steps = 0;
    while (i !== 0 && steps < 4096) {
        steps++;
        const e = ENTRIES.add(STRIDE * i);
        const t = e.readU32();
        const header = e.add(8).readPointer();
        if (t === type && !header.isNull()) {
            const found = readName(header, off);
            if (found !== null && found.toLowerCase() === name.toLowerCase()) {
                return { bucket: b, steps: steps, index: i,
                         header: header.toString(), name: found };
            }
        }
        i = e.add(20).readU32();
    }
    return { bucket: b, steps: steps, header: null };
};
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int)
    ap.add_argument("--samples", type=int, default=6)
    ap.add_argument("--find", action="append", default=[],
                    help="type:name, e.g. 5:mc/mtl_t6_wpn_pda")
    a = ap.parse_args()

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
    r = script.exports_sync.verify(a.samples)

    print()
    print("buckets %d   non-empty chains %d   longest chain %d"
          % (r["buckets"], r["chains"], r["longestChain"]))
    print("entries reached %d   hash reproduces its bucket for %d"
          % (r["entries"], r["exact"]))
    print("  names unreadable %d   types with no accessor %d"
          % (r["unreadableName"], r["unknownType"]))
    checked = r["exact"] + len(r["mismatches"])
    if r["mismatches"]:
        print()
        print("MISMATCHES:")
        for m in r["mismatches"]:
            print("   type %-3d %-48s bucket %d, hashed %d"
                  % (m["type"], m["name"], m["bucket"], m["hashed"]))
    else:
        print("  no mismatches")

    counts = {int(k): v for k, v in r["byType"].items()}
    print()
    print("entries by type (top 10):", dict(Counter(counts).most_common(10)))
    print("name offsets read from funcs_49CACE:",
          {int(k): v for k, v in sorted(r["nameOffsets"].items(), key=lambda kv: int(kv[0]))
           if int(k) in (2, 4, 5, 10, 0, 1, 3)})

    print()
    print("sample assets, with the bucket their name hashes to:")
    for s in r["samples"]:
        print("   type %-3d bucket %-7d %-46s %s"
              % (s["type"], s["bucket"], s["name"][:46], s["header"]))

    for spec in a.find:
        t, _, n = spec.partition(":")
        res = script.exports_sync.find(int(t), n)
        print()
        print("find(type=%s, %r) -> %s" % (t, n, res))
    session.detach()
    return 0 if not r["mismatches"] else 1


if __name__ == "__main__":
    sys.exit(main())
