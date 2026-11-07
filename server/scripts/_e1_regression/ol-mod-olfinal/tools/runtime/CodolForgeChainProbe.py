#!/usr/bin/env python3
"""READ-ONLY walk of a published XModel all the way down to its GPU textures.

Every publication step in this tree has been checked by "the link returned an
entry" and then by "the name is in the asset table". Neither says the assets
point at each other. This walks the chain the renderer would:

    XModel  +68 Material *materials[numsurfs]     (+6 u8 numsurfs)
      -> Material  +92 MaterialTextureDef *table  (+81 u8 textureCount)
           -> MaterialTextureDef  +0 nameHash  +8 GfxImage *image
                -> GfxImage  +0 IDirect3DTexture9  +32 w/h  +44 loadDef  +48 name

and reports, per surface, which material it names, which images that material's
slots hold, and whether each image carries a real texture.

"A real texture" is checked by comparing the object's vtable against a SHIPPED
image's, read from the same process. An earlier version of this probe hardcoded
0x6c6f1438 - the vtable observed in one client - and then reported NO TEXTURE for
six images that were perfectly fine, because d3d9.dll does not load at the same
address twice. A process-local address is not an identity.

Assets are found by the read-only hash walk that mirrors sub_49CA70. Nothing is
called and nothing is written.

A surface whose material is a SHIPPED one is not an error and is reported as
such: until the PPSh's own materials existed, both models were deliberately
linked against `mc/mtl_t6_wpn_pda`.
"""
import sys
import argparse

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


AGENT = r"""
'use strict';
const ENTRIES = ptr(0x239B120);
const HEADS   = ptr(0x1E2D338);
const THUNKS  = ptr(0xE5C8C0);
const STRIDE  = 28;

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
            if (c === 0) return s;
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
            const found = readName(h, off);
            if (found !== null && found.toLowerCase() === name.toLowerCase()) return h;
        }
        i = next;
    }
    return NULL;
}

const SAMPLER = {
    '0xa0ab1041': 'colorMap',
    '0x59d30d0f': 'normalMap',
    '0x34ecccb3': 'specularMap',
    '0xeb529b4d': 'detailMap',
};

function describeImage(img) {
    const rec = { at: img.toString() };
    if (img.isNull()) { rec.error = 'null image pointer'; return rec; }
    try {
        rec.name = readName(img, 48);
        rec.width = img.add(32).readU16();
        rec.height = img.add(34).readU16();
        rec.category = img.add(6).readU8();
        const tex = img.readPointer();
        rec.texture = tex.toString();
        if (tex.isNull()) { rec.hasTexture = false; return rec; }
        rec.hasTexture = true;
        rec.textureVtable = tex.readPointer().toString();
        const ld = img.add(0x2c).readPointer();
        if (!ld.isNull()) {
            rec.format = ld.add(8).readU32();
            rec.resourceSize = ld.add(12).readU32();
        }
    } catch (e) { rec.error = '' + e; }
    return rec;
}

function describeMaterial(mtl) {
    const rec = { at: mtl.toString() };
    if (mtl.isNull()) { rec.error = 'null material pointer'; return rec; }
    try {
        rec.name = readName(mtl, 16);
        const count = mtl.add(81).readU8();
        rec.textureCount = count;
        const table = mtl.add(92).readPointer();
        rec.slots = [];
        for (let i = 0; i < count && i < 16; i++) {
            const e = table.add(12 * i);
            const hash = '0x' + e.readU32().toString(16);
            rec.slots.push({
                index: i,
                nameHash: hash,
                sampler: SAMPLER[hash] || '(unmeasured)',
                semantic: e.add(7).readU8(),
                image: describeImage(e.add(8).readPointer()),
            });
        }
    } catch (e) { rec.error = '' + e; }
    return rec;
}

// The reference vtable, taken from a shipped image in THIS process. Several are
// tried because most images are streamed and not resident at any given moment.
rpc.exports.referenceVtable = function () {
    const REFS = [String.fromCharCode(36) + 'white', 'default', 'missing_fx',
                  'gamefonts_pc', String.fromCharCode(36) + 'black'];
    for (const n of REFS) {
        const img = findAsset(10, n);
        if (img.isNull()) continue;
        try {
            const tex = img.readPointer();
            if (tex.isNull()) continue;
            return { image: n, vtable: tex.readPointer().toString() };
        } catch (e) {}
    }
    return { error: 'no resident shipped image to take a reference vtable from' };
};

rpc.exports.chain = function (modelName) {
    const model = findAsset(4, modelName);
    if (model.isNull()) return { error: "XModel '" + modelName + "' is not in this client" };
    const out = { model: model.toString(), name: readName(model, 0) };
    try {
        out.numBones = model.add(4).readU8();
        out.numRootBones = model.add(5).readU8();
        out.numsurfs = model.add(6).readU8();
        out.lodModelSurfs = '0x' + model.add(72 + 8).readU32().toString(16);
        out.lodResource = readName(model, 72 + 12);
        const materials = model.add(68).readPointer();
        out.surfaces = [];
        const seen = {};
        for (let i = 0; i < out.numsurfs; i++) {
            const m = materials.add(4 * i).readPointer();
            const key = m.toString();
            if (!(key in seen)) seen[key] = describeMaterial(m);
            out.surfaces.push({ surface: i, material: key, name: seen[key].name });
        }
        out.materials = seen;
    } catch (e) { out.error = '' + e; }
    return out;
};
"""

SHIPPED_VTABLE = None   # read from the live process, never hardcoded


def fourcc(v):
    if v is None:
        return "?"
    b = int(v).to_bytes(4, "little")
    if all(32 <= c < 127 for c in b):
        return '"%s"' % b.decode("ascii")
    return str(v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model", nargs="+")
    ap.add_argument("--pid", type=int)
    ap.add_argument("--expect-own", action="store_true",
                    help="fail unless every surface names a material that is not shipped "
                         "and every slot carries a texture")
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

    ref = script.exports_sync.reference_vtable()
    if "error" in ref:
        print(ref["error"])
        session.detach()
        return 2
    global SHIPPED_VTABLE
    SHIPPED_VTABLE = ref["vtable"]
    print("reference texture vtable %s, taken from the shipped image %r"
          % (SHIPPED_VTABLE, ref["image"]))

    problems = 0
    for name in a.model:
        r = script.exports_sync.chain(name)
        print()
        if "error" in r:
            print("%s: %s" % (name, r["error"]))
            problems += 1
            continue
        print("%s  %s" % (r["name"], r["model"]))
        print("   %d bones (%d root), %d surfaces   lodInfo[0].modelSurfs=%s  resource=%r"
              % (r["numBones"], r["numRootBones"], r["numsurfs"],
                 r["lodModelSurfs"], r["lodResource"]))
        for s in r["surfaces"]:
            print("   surface %d -> %s  %s" % (s["surface"], s["name"], s["material"]))
        for at, m in r["materials"].items():
            print()
            print("   material %s  %s  (%d slots)"
                  % (m.get("name"), at, m.get("textureCount", 0)))
            for slot in m.get("slots", []):
                img = slot["image"]
                ok = img.get("hasTexture") and img.get("textureVtable") == SHIPPED_VTABLE
                print("      [%d] %-12s %-11s %-46s %dx%d %s %s"
                      % (slot["index"], slot["sampler"], slot["nameHash"],
                         str(img.get("name"))[:46],
                         img.get("width", 0), img.get("height", 0),
                         fourcc(img.get("format")),
                         "texture ok" if ok else "NO TEXTURE"))
                if not ok:
                    problems += 1
        if a.expect_own:
            for at, m in r["materials"].items():
                if (m.get("name") or "").startswith("mc/"):
                    print("   NOTE: %s is a SHIPPED material, not the port's own"
                          % m.get("name"))
                    problems += 1
    session.detach()
    print()
    print("problems: %d" % problems)
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
