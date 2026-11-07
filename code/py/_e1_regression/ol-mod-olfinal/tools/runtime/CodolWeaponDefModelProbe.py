#!/usr/bin/env python3
"""READ-ONLY: which offsets in a WeaponDef hold XModel pointers?

A published XModel is findable but nothing asks for it. The thing that asks is a
WeaponDef: it names the view model, the world model and the hands. Those offsets
are not decoded in this tree, and guessing them from IW4 notes is exactly the kind
of transfer that has been wrong before here.

They do not need guessing. Every XModel in the client is reachable through the
XAsset hash table, so its header ADDRESS is knowable - and a WeaponDef field that
holds an XModel is a dword equal to one of those addresses. So: build the set of
every type-4 header pointer with its name, then scan a shipped WeaponDef's 4,124
bytes a dword at a time and report every offset that lands on one.

That identifies the fields by what they point AT rather than by where they sit,
and it names the model, so a viewmodel field is recognisable as a viewmodel
(`..._vmgun10`) rather than inferred from position.

The same scan is run over several weapons at once: an offset that holds an XModel
in EVERY weapon is a real field, and one that does so in a single weapon is a
coincidence. With 4,124 bytes and ~11,000 XModels a stray match is not unlikely,
which is why agreement across weapons is the acceptance test rather than a single
hit.

    WeaponDef  asset type 28, 4,124 bytes (0x101C), confirmed by executing the
               engine's own DB_SizeofXAsset dispatch. Name at +0.
"""
import sys
import argparse
from collections import defaultdict

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


AGENT = r"""
'use strict';
const ENTRIES = ptr(0x239B120);
const HEADS   = ptr(0x1E2D338);
const THUNKS  = ptr(0xE5C8C0);
const STRIDE  = 28;
const WEAPONDEF_SIZE = 0x101C;

function nameOffsetFor(type) {
    try {
        const fn = THUNKS.add(4 * type).readPointer().toUInt32();
        if (fn === 0x483390) return 0;
        if (fn === 0x4833A0) return 16;
        if (fn === 0x4833C0) return 48;
        return -1;
    } catch (e) { return -1; }
}

function hashName(type, name) {
    let h = type >>> 0;
    for (let i = 0; i < name.length; i++) {
        let c = name.charCodeAt(i);
        if (c >= 65 && c <= 90) c += 32;
        if (c === 92) c = 47;
        h = (Math.imul(31, h) + c) >>> 0;
    }
    return h % 0x1D4C0;
}

function readName(header, off) {
    try {
        const p = header.add(off).readPointer();
        if (p.isNull()) return null;
        let s = '';
        for (let i = 0; i < 128; i++) {
            const c = p.add(i).readU8();
            if (c === 0) return s.length ? s : null;
            if (c < 32 || c > 126) return null;
            s += String.fromCharCode(c);
        }
        return null;
    } catch (e) { return null; }
}

function findAsset(type, name) {
    const off = nameOffsetFor(type);
    if (off < 0) return NULL;
    let i;
    try { i = HEADS.add(4 * hashName(type, name)).readU32(); } catch (e) { return NULL; }
    for (let steps = 0; i !== 0 && steps < 4096; steps++) {
        const e = ENTRIES.add(STRIDE * i);
        let t, h, next;
        try { t = e.readU32(); h = e.add(8).readPointer(); next = e.add(20).readU32(); }
        catch (err) { return NULL; }
        if (t === type && !h.isNull()) {
            const f = readName(h, off);
            if (f !== null && f.toLowerCase() === name.toLowerCase()) return h;
        }
        i = next;
    }
    return NULL;
}

// Every asset of a type, as address -> name. Built by walking the buckets so it
// needs no assumption about how many entries the array holds.
function assetIndex(type) {
    const off = nameOffsetFor(type);
    const map = {};
    if (off < 0) return map;
    for (let b = 0; b < 0x1D4C0; b++) {
        let i;
        try { i = HEADS.add(4 * b).readU32(); } catch (e) { break; }
        let d = 0;
        while (i !== 0 && d < 64) {
            d++;
            const e = ENTRIES.add(STRIDE * i);
            let t, h;
            try { t = e.readU32(); h = e.add(8).readPointer(); } catch (err) { break; }
            if (t === type && !h.isNull()) {
                const n = readName(h, off);
                if (n !== null) map[h.toString()] = n;
            }
            try { i = e.add(20).readU32(); } catch (err) { break; }
        }
    }
    return map;
}

rpc.exports.weaponNames = function (limit) {
    const out = [];
    const off = nameOffsetFor(28);
    for (let b = 0; b < 0x1D4C0 && out.length < limit; b++) {
        let i;
        try { i = HEADS.add(4 * b).readU32(); } catch (e) { break; }
        let d = 0;
        while (i !== 0 && d < 64) {
            d++;
            const e = ENTRIES.add(STRIDE * i);
            let t, h;
            try { t = e.readU32(); h = e.add(8).readPointer(); } catch (err) { break; }
            if (t === 28 && !h.isNull()) {
                const n = readName(h, off < 0 ? 0 : off);
                if (n !== null && out.length < limit) out.push({ name: n, at: h.toString() });
            }
            try { i = e.add(20).readU32(); } catch (err) { break; }
        }
    }
    return out;
};

rpc.exports.scan = function (weaponNames) {
    const models = assetIndex(4);
    const out = { modelCount: Object.keys(models).length, weapons: [] };
    for (const wn of weaponNames) {
        const w = findAsset(28, wn);
        if (w.isNull()) { out.weapons.push({ name: wn, error: 'not found' }); continue; }
        const hits = [];
        for (let off = 0; off + 4 <= WEAPONDEF_SIZE; off += 4) {
            let v;
            try { v = w.add(off).readPointer(); } catch (e) { continue; }
            if (v.isNull()) continue;
            const key = v.toString();
            if (key in models) hits.push({ off: off, model: models[key], at: key });
        }
        out.weapons.push({ name: wn, at: w.toString(), hits: hits });
    }
    return out;
};
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int)
    ap.add_argument("--weapons", type=int, default=6,
                    help="how many shipped weapons to cross-check")
    ap.add_argument("--name", action="append", default=[],
                    help="scan these weapon names instead of the first N found")
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

    names = a.name
    if not names:
        found = script.exports_sync.weapon_names(a.weapons)
        names = [f["name"] for f in found]
        print("weapons sampled:", names)
    if not names:
        print("no WeaponDefs in this client")
        session.detach()
        return 1

    r = script.exports_sync.scan(names)
    print("XModel assets indexed: %d" % r["modelCount"])

    per_offset = defaultdict(list)
    for w in r["weapons"]:
        print()
        if "error" in w:
            print("  %s: %s" % (w["name"], w["error"]))
            continue
        print("  %s  %s" % (w["name"], w["at"]))
        for h in w["hits"]:
            print("     +%-6d 0x%-5x %-46s %s"
                  % (h["off"], h["off"], h["model"][:46], h["at"]))
            per_offset[h["off"]].append((w["name"], h["model"]))

    weapons_ok = [w for w in r["weapons"] if "error" not in w]
    print()
    print("offsets holding an XModel, by how many of the %d weapons agree:"
          % len(weapons_ok))
    for off in sorted(per_offset, key=lambda o: (-len(per_offset[o]), o)):
        rows = per_offset[off]
        mark = "ALL" if len(rows) == len(weapons_ok) else "   "
        print("   %s +%-6d 0x%-5x  %d/%d   e.g. %s"
              % (mark, off, off, len(rows), len(weapons_ok), rows[0][1]))
    session.detach()
    return 0


if __name__ == "__main__":
    sys.exit(main())
