#!/usr/bin/env python3
"""Publish a CoD4 material into a running client, wearing its OWN images.

This is the last link in the chain. The four data asset types publish by linking;
GfxImage needs a Direct3D upload on the render thread (CodolForgeImageProbe); and
a Material is the thing that binds images to a surface. Until images could be
published, a ported model had to wear a shipped weapon's textures.

WHAT A MATERIAL PORT IS. It is a CLONE, never an authored asset.
`MaterialTextureDef.nameHash` is produced by the asset pipeline and appears
nowhere in the client, so it cannot be recomputed - but it does not have to be.
The hash covers the SAMPLER NAME, so the same slot carries the same hash in every
material that has it:

    colorMap     0xa0ab1041   semantic 2
    normalMap    0x59d30d0f   semantic 5
    specularMap  0x34ecccb3   semantic 8

so a shipped three-slot weapon material can be cloned and its slots rebound by
hash. Only the name and the texture table are replaced; techniqueSet, constants
and state bits keep pointing at the clone's engine-owned memory, which is the
whole point of cloning.

MATCH BY HASH, NEVER BY POSITION. `mc/mtl_t6_wpn_pda` carries its slots in the
order specular, normal, colour. The PPSh's are colour, normal, specular. Matching
by position would put the normal map in the diffuse slot on every surface.

    Material, 104 bytes                 MaterialTextureDef, 12 bytes
      +16  const char *name               +0  u32 nameHash
      +81  u8 textureCount                +4  u8 nameStart, nameEnd,
      +88  techniqueSet                       sampleState, semantic
      +92  MaterialTextureDef *table      +8  GfxImage *image
      +96  constantTable  +100 stateBits

WHERE THE SLOT MAPPING COMES FROM. Not from the `_c`/`_n`/`_s` convention. The
CoD4 material file stores its sampler names as literal strings beside a 12-byte
table of {nameOffset, {sampleState, semantic}, imageOffset}, so the binding is
read out of the package:

    'colorMap'    semantic 02  ->  t4_ppsh41_base_c
    'normalMap'   semantic 05  ->  t4_ppsh41_base_n
    'specularMap' semantic 08  ->  ~t4_ppsh41_base_s-rgb&t4_ppsh~74452df3

and those semantics are the same 2 / 5 / 8 measured across 2,849 shipped
materials.

Assets are resolved by the read-only hash walk that mirrors `sub_49CA70`, never
`DB_FindXAssetHeader` - which blocks and, with createDefault set, would answer a
missing image with the default checker. A surface wearing the default checker
looks like a texture that loaded wrong rather than one that was never there.
"""
import sys
import json
import time
import argparse
import pathlib

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida

from CodolForgeImageProbe import parse_iwi, build_blob, IWI_NAME


# The CoD4 material file: its own texture table says which image goes in which
# slot, so nothing here has to trust a filename suffix.
def parse_cod4_material(path: pathlib.Path):
    d = path.read_bytes()

    def u32(at):
        return int.from_bytes(d[at:at + 4], "little")

    def cstr(at):
        end = d.index(b"\0", at)
        return d[at:end].decode("ascii", "replace")

    name = cstr(u32(0))
    texture_count = d[48]
    table_at = u32(56)
    slots = []
    for i in range(texture_count):
        e = table_at + 12 * i
        slots.append({
            "semantic_name": cstr(u32(e)),
            "sample_state": d[e + 4],
            "semantic": d[e + 5],
            "image": cstr(u32(e + 8)),
        })
    return {"name": name, "textureCount": texture_count, "slots": slots}


AGENT = r"""
'use strict';
const ENTRIES = ptr(0x239B120);
const HEADS   = ptr(0x1E2D338);
const THUNKS  = ptr(0xE5C8C0);
const STRIDE  = 28;
const RENDER_FRAME = ptr(0xBE21F0);
const UPLOAD_RVA = 0x7E7470;
const LINK_RVA   = 0x09DA10;
const SLOT_RVA   = 0x27C080;

const MATERIAL_SIZE = 104;
const OFF_MTL_NAME = 16, OFF_MTL_TEXCOUNT = 81, OFF_MTL_TABLE = 92;
const TEXDEF_STRIDE = 12, OFF_TEX_HASH = 0, OFF_TEX_IMAGE = 8;

let state = null;

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

// sub_49CA70, read-only.
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

function processMalloc() {
    const a = Process.getModuleByName('msvcrt.dll').getExportByName('malloc');
    return new NativeFunction(a, 'pointer', ['uint']);
}

rpc.exports.init = function () {
    const base = Process.findModuleByName('out.exe').base;
    state = {
        base: base,
        malloc: processMalloc(),
        upload: new NativeFunction(base.add(UPLOAD_RVA), 'void', ['pointer', 'pointer']),
        link: new NativeFunction(base.add(LINK_RVA), 'pointer', ['uint32', 'pointer']),
        slotFn: new NativeFunction(base.add(SLOT_RVA), 'uint32', []),
        images: [], done: 0, results: [],
    };
    return { base: base.toString() };
};

// ---- images: stage now, upload on the render thread ------------------------
rpc.exports.stageImage = function (spec) {
    const mem = state.malloc(spec.blob.length);
    if (mem.isNull()) return { error: 'malloc failed' };
    mem.writeByteArray(new Uint8Array(spec.blob).buffer);
    mem.writePointer(mem.add(spec.loaddefAt));      // +0, what sub_BE7470 reads
    mem.add(48).writePointer(mem.add(spec.nameAt)); // +48 name
    state.images.push({ name: spec.name, header: mem, loadDef: mem.add(spec.loaddefAt) });
    return { name: spec.name, storage: mem.toString(), bytes: spec.blob.length };
};

rpc.exports.runUploads = function () {
    Interceptor.attach(RENDER_FRAME, {
        onEnter: function () {
            if (state.done >= state.images.length) return;
            // ONE per frame: a 512x512 DXT5 chain is 349,552 bytes through
            // LockRect and UpdateTexture.
            const job = state.images[state.done++];
            const r = { name: job.name, thread: Process.getCurrentThreadId() };
            try { r.fiberSlot = state.slotFn(); } catch (e) { r.fiberSlot = -1; }
            if (r.fiberSlot !== 1) { r.error = 'wrong fiber slot'; state.results.push(r); return; }
            try { state.upload(job.header, job.header); }
            catch (e) { r.error = 'upload threw: ' + e; state.results.push(r); return; }
            const tex = job.header.readPointer();
            if (tex.isNull()) { r.error = 'no texture created'; state.results.push(r); return; }
            r.texture = tex.toString();
            r.loadDefRelocated = job.header.add(0x2c).readPointer().equals(job.loadDef);
            try {
                const slot = Memory.alloc(4);
                slot.writePointer(job.header);
                const entry = state.link(10, slot);
                r.entry = entry.toString();
                r.published = slot.readPointer().toString();
            } catch (e) { r.error = 'link threw: ' + e; }
            state.results.push(r);
        }
    });
    return { attached: true, queued: state.images.length };
};

rpc.exports.uploadStatus = function () {
    return { done: state.done, total: state.images.length, results: state.results };
};

rpc.exports.stopUploads = function () { Interceptor.detachAll(); return true; };

// ---- the material ----------------------------------------------------------
rpc.exports.inspectClone = function (cloneName) {
    const h = findAsset(5, cloneName);
    if (h.isNull()) return { error: "clone '" + cloneName + "' is not in this client" };
    const count = h.add(OFF_MTL_TEXCOUNT).readU8();
    const table = h.add(OFF_MTL_TABLE).readPointer();
    const slots = [];
    for (let i = 0; i < count; i++) {
        const e = table.add(TEXDEF_STRIDE * i);
        slots.push({
            nameHash: '0x' + e.readU32().toString(16),
            nameStart: String.fromCharCode(e.add(4).readU8()),
            nameEnd: String.fromCharCode(e.add(5).readU8()),
            sampleState: e.add(6).readU8(),
            semantic: e.add(7).readU8(),
            image: e.add(OFF_TEX_IMAGE).readPointer().toString(),
        });
    }
    return { header: h.toString(), textureCount: count, table: table.toString(), slots: slots };
};

// Mirrors SV_BuildForgeMaterial.
rpc.exports.publishMaterial = function (spec, doLink) {
    const out = { steps: [] };
    const clone = findAsset(5, spec.clone);
    if (clone.isNull()) { out.error = "clone '" + spec.clone + "' not found"; return out; }
    const count = clone.add(OFF_MTL_TEXCOUNT).readU8();
    const cloneTable = clone.add(OFF_MTL_TABLE).readPointer();
    if (count === 0 || count > 16 || cloneTable.isNull()) {
        out.error = 'clone has ' + count + ' slots / null table'; return out;
    }

    const nameBytes = spec.name.length + 1;
    const nameAt = MATERIAL_SIZE;
    const tableAt = (nameAt + nameBytes + 3) & ~3;
    const total = tableAt + TEXDEF_STRIDE * count;

    const mem = state.malloc(total);
    if (mem.isNull()) { out.error = 'malloc failed'; return out; }
    for (let i = 0; i < total; i++) mem.add(i).writeU8(0);
    // header, then the clone's texture table, copied verbatim
    for (let i = 0; i < MATERIAL_SIZE; i++) mem.add(i).writeU8(clone.add(i).readU8());
    for (let i = 0; i < spec.name.length; i++)
        mem.add(nameAt + i).writeU8(spec.name.charCodeAt(i));
    for (let i = 0; i < TEXDEF_STRIDE * count; i++)
        mem.add(tableAt + i).writeU8(cloneTable.add(i).readU8());
    out.steps.push('cloned ' + spec.clone + ' (' + count + ' slots) into ' +
                   total + ' bytes at ' + mem);

    const filled = new Array(count).fill(false);
    out.bound = [];
    for (const slot of spec.slots) {
        // Match by nameHash, NEVER by position.
        let at = -1;
        for (let i = 0; i < count; i++) {
            if (mem.add(tableAt + TEXDEF_STRIDE * i + OFF_TEX_HASH).readU32() >>> 0 ===
                (slot.hash >>> 0)) { at = i; break; }
        }
        if (at < 0) { out.error = "the clone has no '" + slot.semantic + "' slot"; return out; }
        if (filled[at]) { out.error = "slot '" + slot.semantic + "' given twice"; return out; }
        const image = findAsset(10, slot.image);
        if (image.isNull()) { out.error = "image '" + slot.image + "' did not resolve"; return out; }
        mem.add(tableAt + TEXDEF_STRIDE * at + OFF_TEX_IMAGE).writePointer(image);
        filled[at] = true;
        // Only the image pointer is replaced. sampleState and semantic stay the
        // CLONE'S - a CoD4 sampleState index is an IW3 value and writing it into
        // an IW5 material would be a cross-engine assumption. Report both so the
        // difference is visible rather than silent.
        const e = mem.add(tableAt + TEXDEF_STRIDE * at);
        out.bound.push({ semantic: slot.semantic, slotIndex: at,
                         image: slot.image, header: image.toString(),
                         cloneSampleState: e.add(6).readU8(),
                         cloneSemantic: e.add(7).readU8(),
                         cod4SampleState: slot.sampleState,
                         cod4Semantic: slot.semantic_value });
    }
    if (filled.some(f => !f)) {
        out.unboundSlots = filled.map((f, i) => f ? -1 : i).filter(i => i >= 0);
    }

    mem.add(OFF_MTL_NAME).writePointer(mem.add(nameAt));
    mem.add(OFF_MTL_TABLE).writePointer(mem.add(tableAt));
    out.steps.push('name and texture table repointed; techniqueSet, constants and ' +
                   'state bits still point at the clone');

    if (!doLink) { out.steps.push('LINK SKIPPED (dry run)'); return out; }
    try {
        const slotPtr = Memory.alloc(4);
        slotPtr.writePointer(mem);
        const entry = state.link(5, slotPtr);
        const published = slotPtr.readPointer();
        out.entry = entry.toString();
        out.published = published.toString();
        if (entry.isNull() || published.isNull()) { out.error = 'link returned nothing'; return out; }
        let same = 0;
        for (let i = 0; i < MATERIAL_SIZE; i++)
            if (published.add(i).readU8() === mem.add(i).readU8()) same++;
        out.headerBytesMatching = same;
        out.steps.push('DB_LinkXAssetEntry(5) returned ' + entry);
    } catch (e) { out.error = 'link threw: ' + e; }
    return out;
};

// Independent read-back: find the material by name and report what its slots
// actually point at, and whether each is the image asset of that name.
rpc.exports.verifyMaterial = function (name, expected) {
    const h = findAsset(5, name);
    if (h.isNull()) return { error: 'not in the asset table' };
    const count = h.add(OFF_MTL_TEXCOUNT).readU8();
    const table = h.add(OFF_MTL_TABLE).readPointer();
    const out = { header: h.toString(), textureCount: count, slots: [] };
    for (let i = 0; i < count; i++) {
        const e = table.add(TEXDEF_STRIDE * i);
        const img = e.add(OFF_TEX_IMAGE).readPointer();
        const rec = { index: i, nameHash: '0x' + e.readU32().toString(16),
                      semantic: e.add(7).readU8(), image: img.toString() };
        try {
            const p = img.add(48).readPointer();
            let s = '';
            for (let k = 0; k < 96; k++) {
                const c = p.add(k).readU8();
                if (c === 0) break;
                s += String.fromCharCode(c);
            }
            rec.imageName = s;
            rec.width = img.add(32).readU16();
            rec.height = img.add(34).readU16();
            rec.texture = '0x' + img.readU32().toString(16);
        } catch (err) { rec.imageName = null; }
        const want = expected[rec.nameHash];
        if (want !== undefined) {
            rec.expected = want;
            rec.matches = (rec.imageName === want) &&
                          findAsset(10, want).equals(img);
        }
        out.slots.push(rec);
    }
    return out;
};
"""

SAMPLER_HASH = {
    "colorMap": 0xA0AB1041,
    "normalMap": 0x59D30D0F,
    "specularMap": 0x34ECCCB3,
    "detailMap": 0xEB529B4D,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("package", type=pathlib.Path,
                    help="the CoD4 package root (has images/ and materials/)")
    ap.add_argument("material", nargs="+", help="material file names under materials/")
    ap.add_argument("--clone", default="mc/mtl_t6_wpn_pda",
                    help="shipped material to clone (default: a 3-slot weapon material)")
    ap.add_argument("--pid", type=int)
    ap.add_argument("--publish-images", action="store_true",
                    help="upload and link the images the materials name")
    ap.add_argument("--link", action="store_true", help="publish the materials")
    ap.add_argument("--seconds", type=float, default=20.0)
    a = ap.parse_args()

    materials = []
    for m in a.material:
        path = a.package / "materials" / m
        if not path.is_file():
            print("no such material file:", path)
            return 2
        materials.append(parse_cod4_material(path))

    print("materials read from the package:")
    wanted_images = []
    for m in materials:
        print("  %s  (%d slots)" % (m["name"], m["textureCount"]))
        for s in m["slots"]:
            known = SAMPLER_HASH.get(s["semantic_name"])
            print("      %-12s semantic %-3d  %-46s %s"
                  % (s["semantic_name"], s["semantic"], s["image"],
                     "hash 0x%08x" % known if known else "NO MEASURED HASH"))
            if known is None:
                print("        refusing: that sampler has no measured nameHash")
                return 2
            if s["image"] not in wanted_images:
                wanted_images.append(s["image"])

    device = frida.get_local_device()
    procs = [q for q in device.enumerate_processes() if q.name.lower() == "out.exe"]
    pid = a.pid or (procs[0].pid if procs else None)
    if pid is None:
        print("no client process found")
        return 2
    print()
    print("clients:", [(p.pid, p.name) for p in procs], "-> using", pid)

    session = device.attach(pid)
    script = session.create_script(AGENT)
    script.load()
    script.exports_sync.init()

    if a.publish_images:
        print()
        print("staging %d images ..." % len(wanted_images))
        for name in wanted_images:
            path = a.package / "images" / (name + ".iwi")
            if not path.is_file():
                print("  MISSING %s" % path)
                return 2
            src = parse_iwi(path)
            built = build_blob(src, name, 2, 3)
            r = script.exports_sync.stage_image({
                "name": name,
                "blob": list(built["blob"]),
                "nameAt": built["name_at"],
                "loaddefAt": built["loaddef_at"],
            })
            print("  %-46s %s %dx%d %d levels -> %s"
                  % (name[:46], IWI_NAME.get(src["fmt"], "?"), src["w"], src["h"],
                     src["stored"], r.get("storage", r.get("error"))))
        script.exports_sync.run_uploads()
        deadline = time.time() + a.seconds
        status = None
        while time.time() < deadline:
            time.sleep(0.3)
            status = script.exports_sync.upload_status()
            if status["done"] >= status["total"]:
                break
        script.exports_sync.stop_uploads()
        print()
        print("uploads: %d/%d" % (status["done"], status["total"]))
        for r in status["results"]:
            print("  %-46s %s" % (
                r["name"][:46],
                r.get("error") or ("texture %s  entry %s  relocated=%s"
                                   % (r.get("texture"), r.get("entry"),
                                      r.get("loadDefRelocated")))))
        if status["done"] < status["total"]:
            print("not every image uploaded; stopping before the materials")
            return 1

    print()
    clone = script.exports_sync.inspect_clone(a.clone)
    print("clone %s:" % a.clone)
    print(json.dumps(clone, indent=2))
    if "error" in clone:
        session.detach()
        return 1

    failures = 0
    for m in materials:
        spec = {
            "name": m["name"],
            "clone": a.clone,
            "slots": [{"semantic": s["semantic_name"],
                       "hash": SAMPLER_HASH[s["semantic_name"]],
                       "image": s["image"],
                       "sampleState": s["sample_state"],
                       "semantic_value": s["semantic"]} for s in m["slots"]],
        }
        print()
        print("=== %s" % m["name"])
        r = script.exports_sync.publish_material(spec, a.link)
        print(json.dumps(r, indent=2))
        if "error" in r:
            failures += 1
            continue
        if a.link:
            expected = {("0x%x" % SAMPLER_HASH[s["semantic_name"]]): s["image"]
                        for s in m["slots"]}
            v = script.exports_sync.verify_material(m["name"], expected)
            print("read back from the asset table:")
            print(json.dumps(v, indent=2))
            if "error" in v or not all(
                    s.get("matches", False) for s in v["slots"] if "expected" in s):
                failures += 1
    session.detach()
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
