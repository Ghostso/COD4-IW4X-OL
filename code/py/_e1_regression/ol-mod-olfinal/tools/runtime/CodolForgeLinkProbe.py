#!/usr/bin/env python3
"""Publish one CodolForge-emitted XAnimParts into a running client.

Mirrors sv_forge_publish_mp exactly: relocate the blob's pointer placeholders
into owned memory, resolve bone names by WALKING the script-string table, then
call DB_LinkXAssetEntry(2, &header).

Memory comes from the process's own malloc, not Frida's Memory.alloc, because the
engine keeps every pointer inside the header and Frida frees its allocations on
detach - which would leave the asset hash pointing at freed memory.

Verification reads the published pointer back and compares it byte for byte
against what was written. It deliberately does NOT call DB_FindXAssetHeader:
that function waits on a streaming event and takes different paths depending on
the calling thread, so it is not safe to call from an arbitrary one.

CODREF: DB_LinkXAssetEntry sub_49DA10(u32 type, void **header), __cdecl. It reads
the asset's name through a per-type accessor, hashes it, and for a name it has not
seen allocates an entry, memcpy's DB_SizeofXAsset(type) bytes, and inserts it. It
takes no locks and makes no thread checks, which is why it is safe to call here
when DB_FindXAssetHeader is not.
"""
import sys
import json
import argparse
from pathlib import Path

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


AGENT = r"""
'use strict';
const LINK_RVA = 0x09DA10;
const STRTAB_RVA = 0x749C524;

function resolveScriptString(base, name) {
    const table = base.add(STRTAB_RVA).readPointer();
    if (table.isNull()) return 0;
    const want = name.length + 1;              // length counts the NUL
    for (let i = 1; i <= 0xFFFF; i++) {
        const e = table.add(20 * i);
        if (e.add(3).readU8() !== want) continue;
        let match = true;
        for (let k = 0; k < name.length; k++) {
            if (e.add(4 + k).readU8() !== name.charCodeAt(k)) { match = false; break; }
        }
        if (match && e.add(4 + name.length).readU8() === 0) return i;
    }
    return 0;
}

// Interning is the ONE thing the table walk cannot do. A port's bone names are
// always already present, but its notify names are not: `t4_ppsh_mag_out` is a
// CoD4 script event this client has never seen. sub_74BD10 exists for exactly
// that, and the zone loader calls it with kind 4 and strlen + 1.
//
// It takes a critical section and allocates from the engine's string pool, so it
// is opt-in. The result is READ BACK from the table rather than trusted: a wrong
// calling convention could return a plausible integer and have written nothing.
function internScriptString(base, name) {
    const INTERN_RVA = 0x34BD10;
    const fn = new NativeFunction(base.add(INTERN_RVA), 'int',
        ['pointer', 'int', 'uint']);
    const buf = Memory.allocUtf8String(name);
    const id = fn(buf, 4, name.length + 1);
    if (id <= 0 || id > 0xFFFF) return 0;
    // Read it back: the table must now hold this exact name at this exact index.
    const table = base.add(STRTAB_RVA).readPointer();
    const e = table.add(20 * id);
    if (e.add(3).readU8() !== name.length + 1) return 0;
    for (let k = 0; k < name.length; k++) {
        if (e.add(4 + k).readU8() !== name.charCodeAt(k)) return 0;
    }
    return id;
}

rpc.exports.publish = function (bytes, boneNames, notifyNames, doLink, mayIntern) {
    const out = { steps: [] };
    const base = Process.findModuleByName('out.exe').base;
    // Frida 17 moved the module export helpers; try the current form first.
    let mallocAddr = null;
    try { mallocAddr = Process.getModuleByName('msvcrt.dll').getExportByName('malloc'); }
    catch (e) {
        try { mallocAddr = Module.getGlobalExportByName('malloc'); }
        catch (e2) { out.error = 'cannot resolve malloc: ' + e2; return out; }
    }
    const malloc = new NativeFunction(mallocAddr, 'pointer', ['uint']);

    const size = bytes.length;
    const mem = malloc(size);
    if (mem.isNull()) { out.error = 'malloc failed'; return out; }
    for (let i = 0; i < size; i++) mem.add(i).writeU8(bytes[i]);
    out.steps.push('copied ' + size + ' bytes to ' + mem);

    const u16 = o => mem.add(o).readU16();
    const u32 = o => mem.add(o).readU32();
    const dB = u16(4), dS = u16(6), dI = u16(8), rB = u16(10);
    const bones = mem.add(26).readU8(), notifies = mem.add(27).readU8();
    const rS = u32(32);
    out.header = { dataByte: dB, dataShort: dS, dataInt: dI, randomDataByte: rB,
                   randomDataShort: rS, bones: bones, notifies: notifies,
                   numframes: u16(14) };
    if (bones !== boneNames.length) { out.error = 'bone count mismatch'; return out; }

    // Relocate, in the loader's own visit order. The stream is packed.
    let p = 88;
    const claim = (off, n) => {
        const ph = u32(off);
        if (ph === 0) return true;
        if (ph !== 0xFFFFFFFF) { out.error = 'bad placeholder at +' + off; return false; }
        mem.add(off).writePointer(mem.add(p));
        p += n;
        return true;
    };
    let nameStr = '';
    if (u32(0) === 0xFFFFFFFF) {
        let e = p;
        while (mem.add(e).readU8() !== 0) e++;
        nameStr = mem.add(p).readCString();
        mem.add(0).writePointer(mem.add(p));
        p = e + 1;
    }
    const namesAt = p;
    if (!claim(48, 2 * bones)) return out;
    const notifyAt = p;
    if (!claim(80, 8 * notifies)) return out;
    if (!claim(52, dB)) return out;
    if (!claim(56, 2 * dS)) return out;
    if (!claim(60, 4 * dI)) return out;
    if (!claim(64, 2 * rS)) return out;
    if (!claim(68, rB)) return out;
    if (p !== size) { out.error = 'arrays tile ' + p + ' of ' + size; return out; }
    out.name = nameStr;
    out.steps.push('relocated; arrays tile the blob exactly');

    const resolved = [];
    for (let i = 0; i < bones; i++) {
        const id = resolveScriptString(base, boneNames[i]);
        if (id === 0) { out.error = "bone '" + boneNames[i] + "' did not resolve"; return out; }
        mem.add(namesAt + 2 * i).writeU16(id);
        if (resolved.length < 6) resolved.push({ bone: boneNames[i], index: id });
    }
    out.interned = [];
    for (let i = 0; i < notifies; i++) {
        let id = resolveScriptString(base, notifyNames[i]);
        if (id === 0 && mayIntern) {
            id = internScriptString(base, notifyNames[i]);
            if (id !== 0) out.interned.push({ name: notifyNames[i], index: id });
        }
        if (id === 0) {
            out.error = "notify '" + notifyNames[i] + "' did not resolve" +
                (mayIntern ? " and could not be interned" : "");
            return out;
        }
        mem.add(notifyAt + 8 * i).writeU16(id);
    }
    out.resolvedSample = resolved;
    out.steps.push('resolved ' + bones + ' bone names and ' + notifies + ' notifies');

    if (!doLink) { out.steps.push('LINK SKIPPED (dry run)'); return out; }

    const before = [];
    for (let i = 0; i < 88; i++) before.push(mem.add(i).readU8());

    const link = new NativeFunction(base.add(LINK_RVA), 'pointer', ['uint32', 'pointer']);
    const slot = Memory.alloc(4);
    slot.writePointer(mem);
    let entry;
    try { entry = link(2, slot); }
    catch (e) { out.error = 'link threw: ' + e; return out; }
    const published = slot.readPointer();
    out.entry = entry.toString();
    out.published = published.toString();
    out.steps.push('DB_LinkXAssetEntry(2) returned entry ' + entry);

    if (entry.isNull() || published.isNull()) { out.error = 'link returned nothing'; return out; }
    let same = 0;
    for (let i = 0; i < 88; i++) if (published.add(i).readU8() === before[i]) same++;
    out.headerBytesMatching = same;
    out.publishedIsOurs = published.equals(mem);
    return out;
};
"""


def readNames(path: Path) -> tuple[list[str], list[str]]:
    bones: list[str] = []
    notifies: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        key, _, val = line.partition("\t")
        (notifies if key.startswith("notify") else bones).append(val.strip())
    return bones, notifies


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", type=Path,
                    help="a .xanimparts file, or a directory of them")
    ap.add_argument("--pid", type=int)
    ap.add_argument("--intern", action="store_true",
                    help="call sub_74BD10 to add script strings the client lacks; "
                         "needed only for notify names")
    ap.add_argument("--link", action="store_true",
                    help="actually call DB_LinkXAssetEntry; without it, relocate and "
                         "resolve only")
    a = ap.parse_args()

    assets = (sorted(a.target.glob("*.xanimparts")) if a.target.is_dir()
              else [a.target])
    if not assets:
        print("no .xanimparts found under", a.target)
        return 2

    device = frida.get_local_device()
    procs = [q for q in device.enumerate_processes() if q.name.lower() == "out.exe"]
    pid = a.pid or (procs[0].pid if procs else None)
    if pid is None:
        print("no client process found")
        return 2
    print("clients:", [(p.pid, p.name) for p in procs], "-> using", pid)
    print("assets: %d   link=%s" % (len(assets), a.link))

    # One attach for the whole set: repeated attach/detach churns the client for
    # no reason, and every asset wants the same script-string table anyway.
    session = device.attach(pid)
    script = session.create_script(AGENT)
    script.load()

    published = 0
    failures: list[tuple[str, str]] = []
    for asset in assets:
        names = asset.with_suffix("").with_suffix("")
        names = asset.parent / (asset.stem + ".names.tsv")
        if not names.exists():
            failures.append((asset.stem, "no .names.tsv beside the asset"))
            continue
        bones, notifies = readNames(names)
        result = script.exports_sync.publish(
            list(asset.read_bytes()), bones, notifies, a.link, a.intern)
        if "error" in result:
            failures.append((asset.stem, result["error"]))
            print("  FAIL  %-28s %s" % (asset.stem, result["error"]))
            continue
        published += 1
        for entry in result.get("interned", []):
            print("        interned '%s' as script string %d"
                  % (entry["name"], entry["index"]))
        print("  ok    %-28s %d bones, %d notifies, %s -> entry %s"
              % (asset.stem, result["header"]["bones"], result["header"]["notifies"],
                 "%d bytes" % len(asset.read_bytes()),
                 result.get("entry", "(dry run)")))

    print()
    print("%d of %d %s" % (published, len(assets),
                           "linked" if a.link else "relocated and resolved"))
    for name, why in failures:
        print("  FAILED %-28s %s" % (name, why))
    session.detach()
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
