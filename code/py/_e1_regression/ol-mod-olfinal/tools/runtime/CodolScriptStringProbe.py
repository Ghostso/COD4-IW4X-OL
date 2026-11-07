#!/usr/bin/env python3
"""READ-ONLY probe of a running client's script-string table.

Calls nothing. Reads *(void **)(out.exe + 0x749C524) and walks the 20-byte
entries the intern function `sub_74BD10` writes:

    +0 u16 refcount   +2 u8 kind   +3 u8 length (INCLUDING the NUL)   +4.. name

Written to check, before anything is asked to execute, that the table address and
layout recovered from Load_XAnimParts' remap chain are actually right - and that
bone names are interned with kind 4, the kind the zone loader passes.

The indices this prints are PER PROCESS and depend on load order. Two clients on
the same machine give a bone different indices, which is exactly why an emitted
XAnimParts cannot carry them and must have its `names` array patched at publish
time.
"""
import sys, json
from CodolFridaRuntime import configure_frida_runtime
configure_frida_runtime()
import frida

WANT = ["j_gun", "tag_camera", "tag_weapon", "j_bolt", "colorMap", "j_shoulder_le", "tag_torso"]

AGENT = r"""
'use strict';
function hex(p, n) {
    let s = '';
    for (let i = 0; i < n; i++) s += p.add(i).readU8().toString(16).padStart(2, '0') + ' ';
    return s;
}
function txt(p, n) {
    let s = '';
    for (let i = 0; i < n; i++) { const c = p.add(i).readU8(); s += (c >= 32 && c < 127) ? String.fromCharCode(c) : '.'; }
    return s;
}
rpc.exports.probe = function (want) {
    const mod = Process.findModuleByName('out.exe');
    const slot = mod.base.add(0x749C524);
    const table = slot.readPointer();
    const out = { base: mod.base.toString(), table: table.toString() };
    out.tableHex = hex(table, 80);
    out.tableTxt = txt(table, 80);
    const wanted = new Set(want);
    out.found = {};
    let live = 0;
    for (let i = 1; i < 200000; i++) {
        const e = table.add(20 * i);
        let len, refs;
        try { refs = e.readU16(); len = e.add(3).readU8(); } catch (err) { out.stoppedAt = i; break; }
        if (len === 0 || len > 16) continue;
        let name = '';
        for (let k = 0; k < len - 1; k++) {
            const c = e.add(4 + k).readU8();
            if (c === 0) break;
            name += String.fromCharCode(c);
        }
        if (name.length === 0) continue;
        live++;
        if (wanted.has(name) && !(name in out.found)) {
            out.found[name] = { index: i, kind: e.add(2).readU8(), refs: refs, len: len };
        }
    }
    out.liveEntries = live;
    return out;
};
"""
device = frida.get_local_device()
procs = [q for q in device.enumerate_processes() if q.name.lower() == "out.exe"]
print("processes:", [(p.pid, p.name) for p in procs])
for p in procs:
    print("=== pid %d ===" % p.pid)
    try:
        s = device.attach(p.pid)
        sc = s.create_script(AGENT); sc.load()
        r = sc.exports_sync.probe(WANT)
        print("  base=%s table=%s liveEntries=%s stoppedAt=%s" %
              (r["base"], r["table"], r.get("liveEntries"), r.get("stoppedAt")))
        print("  raw:", r["tableHex"][:120])
        print("  txt: |%s|" % r["tableTxt"])
        print("  found:", json.dumps(r["found"]))
        s.detach()
    except Exception as e:
        print("  FAILED:", type(e).__name__, e)
