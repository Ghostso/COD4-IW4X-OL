#!/usr/bin/env python3
"""Publish a CodolForge-emitted XModel into a running client.

Mirrors SV_BuildForgeXModel: build the 360-byte header plus everything it points
at, from the bundle's own pieces, then call DB_LinkXAssetEntry(4, &header).

Two things differ from the C++ path, and both are improvements the live client
forced:

  * bone names resolve by WALKING the script-string table, not by calling the
    intern function;
  * materials resolve by WALKING the XAsset entry table at 0x239B120, not by
    calling DB_FindXAssetHeader - which blocks on a streaming event and branches
    on the calling thread id, and so cannot be driven from here at all.

Both walks are read-only, which is what makes this safe to run against a live
client.

CODREF(xmodel): Load_XModel out.exe 0x489B20, array lengths from its own register
loads. nonRoot = numBones - numRootBones.

    +44 boneNames  u16  x numBones      +48 parentList  u8    x nonRoot
    +52 quats      i16  x 4*nonRoot     +56 trans       float x 3*nonRoot
    +60 partClass  u8   x numBones      +64 baseMat     32    x numBones
    +68 materials  ptr  x numsurfs      +72 XModelLodInfo[4], 56 bytes each
    +300 collSurfs (+304 count)  +312 boneInfo  +352 physPreset  +356 physCollmap
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
const ENTRIES = ptr(0x239B120);
const HEADS   = ptr(0x1E2D338);
const THUNKS  = ptr(0xE5C8C0);
const STRIDE = 28;

function resolveScriptString(base, name) {
    const table = base.add(STRTAB_RVA).readPointer();
    if (table.isNull()) return 0;
    const want = name.length + 1;
    for (let i = 1; i <= 0xFFFF; i++) {
        const e = table.add(20 * i);
        if (e.add(3).readU8() !== want) continue;
        let ok = true;
        for (let k = 0; k < name.length; k++) {
            if (e.add(4 + k).readU8() !== name.charCodeAt(k)) { ok = false; break; }
        }
        if (ok && e.add(4 + name.length).readU8() === 0) return i;
    }
    return 0;
}

// Read-only stand-in for DB_FindXAssetHeader, mirroring sub_49CA70 exactly.
//
// DB_FindXAssetHeader takes a critical section, waits on a streaming event and
// branches on GetCurrentThreadId, so it cannot be driven from here. Its LOOKUP
// has none of that:
//
//     bucket = sub_49C870(type, name)          h = type; h = 31*h + fold(c)
//     for (i = heads[bucket]; i; i = e.next)   heads dword_1E2D338
//         if (e.type == type && iequals(...))  entries dword_239B120, stride 28
//
// The name's offset comes from funcs_49CACE at 0xE5C8C0, the engine's own per-type
// accessor: 0x483390 -> +0, 0x4833A0 -> +16, 0x4833C0 -> +48.
//
// Verified against a live client: over all 120,000 buckets, every one of 81,128
// assets whose type has a known accessor hashes back to the bucket it was found
// in. The longest chain is 7, so this replaces a 200,000-entry linear scan.
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
        if (c >= 65 && c <= 90) c += 32;   // tolower
        if (c === 92) c = 47;              // the HASH folds a backslash; the compare does not
        h = (Math.imul(31, h) + c) >>> 0;
    }
    return h % 0x1D4C0;
}

function findAsset(type, name) {
    const off = nameOffsetFor(type);
    if (off < 0) return NULL;
    let i;
    try { i = HEADS.add(4 * hashName(type, name)).readU32(); } catch (e) { return NULL; }
    for (let steps = 0; i !== 0 && steps < 4096; steps++) {
        const e = ENTRIES.add(STRIDE * i);
        let t, h, next;
        try {
            t = e.readU32();
            h = e.add(8).readPointer();
            next = e.add(20).readU32();
        } catch (err) { return NULL; }
        if (t === type && !h.isNull()) {
            try {
                const p = h.add(off).readPointer();
                if (!p.isNull()) {
                    let ok = true;
                    for (let k = 0; k <= name.length; k++) {
                        let a = p.add(k).readU8();
                        let b = k < name.length ? name.charCodeAt(k) : 0;
                        if (a >= 65 && a <= 90) a += 32;
                        if (b >= 65 && b <= 90) b += 32;
                        if (a !== b) { ok = false; break; }
                    }
                    if (ok) return h;
                }
            } catch (err) {}
        }
        i = next;
    }
    return NULL;
}

rpc.exports.publish = function (spec, doLink) {
    const out = { steps: [] };
    const base = Process.findModuleByName('out.exe').base;
    let mallocAddr;
    try { mallocAddr = Process.getModuleByName('msvcrt.dll').getExportByName('malloc'); }
    catch (e) { out.error = 'cannot resolve malloc'; return out; }
    const malloc = new NativeFunction(mallocAddr, 'pointer', ['uint']);

    const header = spec.header;
    const bones = header[4], roots = header[5], surfs = header[6];
    const nonRoot = bones - roots;
    out.scalars = { bones: bones, roots: roots, surfs: surfs, nonRoot: nonRoot };
    if (spec.boneNames.length !== bones) { out.error = 'bone name count mismatch'; return out; }
    if (spec.materials.length !== surfs) { out.error = 'material count mismatch'; return out; }

    const align4 = v => (v + 3) & ~3;
    let p = 360;
    const nameAt = p;            p += spec.name.length + 1;
    p = (p + 1) & ~1;
    const boneNamesAt = p;       p += 2 * bones;
    const parentAt = p;          p += nonRoot;
    p = align4(p);
    const quatsAt = p;           p += spec.quats.length;
    const transAt = p;           p += spec.trans.length;
    const partAt = p;            p += bones;
    p = align4(p);
    const baseMatAt = p;         p += spec.baseMat.length;
    const materialsAt = p;       p += 4 * surfs;
    const lodNameAt = p;         p += spec.resource.length + 1;
    const total = p;

    const mem = malloc(total);
    if (mem.isNull()) { out.error = 'malloc failed'; return out; }
    for (let i = 0; i < total; i++) mem.add(i).writeU8(0);
    for (let i = 0; i < 360; i++) mem.add(i).writeU8(header[i]);
    const put = (at, arr) => { for (let i = 0; i < arr.length; i++) mem.add(at + i).writeU8(arr[i]); };
    for (let i = 0; i < spec.name.length; i++) mem.add(nameAt + i).writeU8(spec.name.charCodeAt(i));
    for (let i = 0; i < spec.resource.length; i++) mem.add(lodNameAt + i).writeU8(spec.resource.charCodeAt(i));
    put(parentAt, spec.parentList);
    put(quatsAt, spec.quats);
    put(transAt, spec.trans);
    put(partAt, spec.partClass);
    put(baseMatAt, spec.baseMat);
    out.steps.push('laid out ' + total + ' bytes at ' + mem);

    const resolvedBones = [];
    for (let i = 0; i < bones; i++) {
        const id = resolveScriptString(base, spec.boneNames[i]);
        if (id === 0) { out.error = "bone '" + spec.boneNames[i] + "' did not resolve"; return out; }
        mem.add(boneNamesAt + 2 * i).writeU16(id);
        resolvedBones.push({ bone: spec.boneNames[i], index: id });
    }
    out.bones = resolvedBones;

    const resolvedMaterials = [];
    for (let i = 0; i < surfs; i++) {
        const m = findAsset(5, spec.materials[i]);
        if (m.isNull()) { out.error = "material '" + spec.materials[i] + "' not in the client"; return out; }
        mem.add(materialsAt + 4 * i).writePointer(m);
        resolvedMaterials.push({ material: spec.materials[i], header: m.toString() });
    }
    out.materials = resolvedMaterials;

    mem.add(0).writePointer(mem.add(nameAt));
    mem.add(44).writePointer(mem.add(boneNamesAt));
    mem.add(48).writePointer(nonRoot ? mem.add(parentAt) : NULL);
    mem.add(52).writePointer(nonRoot ? mem.add(quatsAt) : NULL);
    mem.add(56).writePointer(nonRoot ? mem.add(transAt) : NULL);
    mem.add(60).writePointer(mem.add(partAt));
    mem.add(64).writePointer(mem.add(baseMatAt));
    mem.add(68).writePointer(surfs ? mem.add(materialsAt) : NULL);
    mem.add(72 + 12).writePointer(mem.add(lodNameAt));   // lodInfo[0].name
    mem.add(72 + 48).writePointer(NULL);                 // lodInfo[0].surfs
    for (let lod = 1; lod < 4; lod++) {
        const at = 72 + lod * 56;
        mem.add(at + 8).writeU32(0);
        mem.add(at + 12).writePointer(NULL);
        mem.add(at + 48).writePointer(NULL);
    }
    mem.add(300).writePointer(NULL); mem.add(304).writeU32(0);
    mem.add(312).writePointer(NULL);
    mem.add(352).writePointer(NULL); mem.add(356).writePointer(NULL);
    out.steps.push('pointers wired; lodInfo[0].modelSurfs = 0x' +
        mem.add(72 + 8).readU32().toString(16));

    if (!doLink) { out.steps.push('LINK SKIPPED (dry run)'); return out; }

    const before = [];
    for (let i = 0; i < 360; i++) before.push(mem.add(i).readU8());
    const link = new NativeFunction(base.add(LINK_RVA), 'pointer', ['uint32', 'pointer']);
    const slot = Memory.alloc(4);
    slot.writePointer(mem);
    let entry;
    try { entry = link(4, slot); } catch (e) { out.error = 'link threw: ' + e; return out; }
    const published = slot.readPointer();
    out.entry = entry.toString();
    out.published = published.toString();
    if (entry.isNull() || published.isNull()) { out.error = 'link returned nothing'; return out; }
    let same = 0;
    for (let i = 0; i < 360; i++) if (published.add(i).readU8() === before[i]) same++;
    out.headerBytesMatching = same;
    out.steps.push('DB_LinkXAssetEntry(4) returned entry ' + entry);
    return out;
};
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle", type=Path)
    ap.add_argument("model")
    ap.add_argument("--material", action="append", default=[],
                    help="override every surface with this shipped material "
                         "(repeatable, one per surface)")
    ap.add_argument("--pid", type=int)
    ap.add_argument("--link", action="store_true")
    a = ap.parse_args()

    doc = json.loads(a.bundle.read_text(encoding="utf-8"))
    model = next((m for m in doc["models"] if m["name"] == a.model), None)
    if model is None:
        print("no model named", a.model)
        return 2
    skeleton = doc["skeletons"][model["skeleton_key"]]
    hexb = lambda k: list(bytes.fromhex(skeleton[k]))

    materials = list(model["materials"])
    if a.material:
        materials = [a.material[i % len(a.material)] for i in range(len(materials))]

    spec = {
        "name": model["name"],
        "resource": model["resources"][0],
        "header": list(bytes.fromhex(model["header_hex"])),
        "boneNames": skeleton["bone_names"],
        "parentList": hexb("parent_list_hex"),
        "quats": hexb("quats_hex"),
        "trans": hexb("translations_hex"),
        "partClass": hexb("part_classification_hex"),
        "baseMat": hexb("base_matrices_hex"),
        "materials": materials,
    }

    device = frida.get_local_device()
    procs = [q for q in device.enumerate_processes() if q.name.lower() == "out.exe"]
    pid = a.pid or (procs[0].pid if procs else None)
    if pid is None:
        print("no client process found")
        return 2
    print("clients:", [(p.pid, p.name) for p in procs], "-> using", pid)
    print("model: %s  resource=%s  materials=%s  link=%s"
          % (spec["name"], spec["resource"], materials, a.link))

    session = device.attach(pid)
    script = session.create_script(AGENT)
    script.load()
    r = script.exports_sync.publish(spec, a.link)
    print(json.dumps(r, indent=2))
    session.detach()
    return 0 if "error" not in r else 1


if __name__ == "__main__":
    sys.exit(main())
