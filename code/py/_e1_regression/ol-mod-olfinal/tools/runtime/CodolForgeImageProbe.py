#!/usr/bin/env python3
"""Publish a GfxImage into a running client, from the render thread.

This is the fifth publication path, and the only one that is not a pure link.
A GfxImage's +0 is an IDirect3DTexture9 that does not exist until sub_BE7470
creates it, and the device carries BehaviorFlags 0x42 - no D3DCREATE_MULTITHREADED
- so that call has to happen on the thread that owns the device. Measured: that
is NOT the thread running Com_Frame.

    thread 16016  Com_Frame  0x4FEA20       923 calls in 5s
    thread 43208  sub_BE21F0 0xBE21F0       923 calls in 5s, and every
                  BeginScene / Clear / SetRenderTarget in the process

So the work rides sub_BE21F0, the render backend's per-frame function. This
attaches there, does the upload on the first frame it sees, and detaches - which
is exactly what ol-mod's ClientRenderFrameHook does with a five-byte call-site
patch at 0xBE220E instead of an interceptor.

WHAT IT BUILDS, and why each field is what it is:

    GfxImage, 52 bytes                    GfxImageLoadDef, 16 bytes + pixels
      +0   -> the load def, going in        +0   u8  Levels for CreateTexture
              the texture, coming out                (0 = full chain, 1 = one)
      +4   u8 mapType 3 (2D)                +4   u32 flags, bit 1 = single mip
      +5   u8 semantic                      +8   u32 D3DFORMAT
      +6   u8 category 3                    +12  u32 resourceSize
      +16  u32 cardMemory[4]                +16  the chain, largest level first
      +32  u16 width, height, depth
      +38  u8 0   "no pixels"
      +40  u8 0   sub_4999E0 returns true - and sub_BE7470 does NOTHING - when
                  (b & 1) is set and (b & 2) is not, so this must be 0
      +48  const char *name

`sub_BE7470` opens with `sub_67C170(1, sub_BE0900)`, a FIBER switch rather than
a thread hop: it returns immediately when the caller is already on context 1,
and otherwise yields until the scheduler grants it. --upload reads and reports
the fiber slot before doing anything, so the first run measures that rather than
assuming it.

Nothing is written to the client unless --upload is given, and nothing is
published unless --link is given as well. Memory comes from the process's own
malloc, never Frida's, because a published asset outlives the script.
"""
import sys
import json
import argparse
import time
import pathlib

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


# ---------------------------------------------------------------- IWI, in Python
# The same rules as sv_forge_image_mp.cpp. Duplicated on purpose: if the two
# disagree, the C++ is wrong, and the C++ is what ships.

IWI_BLOCK = {11: 8, 12: 16, 13: 16}
IWI_BPP = {1: 4, 3: 2, 4: 1, 5: 1}
IWI_NAME = {1: "A8R8G8B8", 2: "X8R8G8B8", 3: "A8L8", 4: "L8", 5: "A8",
            11: "DXT1", 12: "DXT3", 13: "DXT5"}
TO_D3D = {1: 21, 3: 51, 4: 50, 5: 28,
          11: 0x31545844, 12: 0x33545844, 13: 0x35545844}


def level_bytes(fmt, w, h, d):
    """sub_BE8690, branch for branch."""
    if fmt > 80:
        if fmt > 0x31545844:
            if fmt in (0x33545844, 0x35545844):
                return 16 * d * ((h + 3) >> 2) * ((w + 3) >> 2)
        else:
            if fmt == 0x31545844:
                return 8 * d * ((h + 3) >> 2) * ((w + 3) >> 2)
            if fmt in (112, 114):
                return 4 * d * h * w
        return 0
    if fmt == 80:
        return 2 * d * h * w
    if fmt in (21, 22, 75):
        return 4 * d * h * w
    if fmt in (28, 50):
        return d * h * w
    if fmt == 51:
        return 2 * d * h * w
    return 0


def level_count(flags, w, h, d):
    """sub_BE8C30. Only the low byte is read, and only bit 1."""
    if (flags & 0xFF) & 2:
        return 1
    n, i = 1, 1
    while i < w or i < h or i < d:
        n += 1
        i *= 2
    return n


def iwi_level_bytes(f, w, h):
    w, h = max(1, w), max(1, h)
    bb = IWI_BLOCK.get(f)
    if bb:
        return ((w + 3) // 4) * ((h + 3) // 4) * bb
    return w * h * IWI_BPP.get(f, 0)


def parse_iwi(path: pathlib.Path):
    d = path.read_bytes()
    if d[:3] != b"IWi":
        raise SystemExit("%s is not an IWi file" % path)
    ver = d[3]
    if ver == 6:
        hs, fmt, cube = 28, d[4], False
        w = int.from_bytes(d[6:8], "little")
        h = int.from_bytes(d[8:10], "little")
        dep = int.from_bytes(d[10:12], "little")
        smallest_first = False
    elif ver in (8, 9):
        hs = 32
        flags = int.from_bytes(d[4:8], "little")
        fmt = d[8]
        cube = bool(flags & 0x10000)
        w = int.from_bytes(d[10:12], "little")
        h = int.from_bytes(d[12:14], "little")
        dep = int.from_bytes(d[14:16], "little")
        smallest_first = True
    else:
        raise SystemExit("unsupported IWi version %d" % ver)

    d3d = TO_D3D.get(fmt)
    if d3d is None:
        raise SystemExit("IWi format %d (%s) has no plain D3DFORMAT this path copies"
                         % (fmt, IWI_NAME.get(fmt, "?")))
    payload = d[hs:]
    faces = 6 if cube else 1
    depth = max(1, dep)

    m, full = max(w, h, depth), 1
    while m > 1:
        m >>= 1
        full += 1

    total, stored, sizes = 0, 0, []
    for i in range(full):
        s = iwi_level_bytes(fmt, w >> i, h >> i) * faces
        sizes.append(s)
        total += s
        if total == len(payload):
            stored = i + 1
            break
        if total > len(payload):
            break
    if stored == 0:
        raise SystemExit("no mip count from 1..%d fills the %d-byte payload"
                         % (full, len(payload)))

    return dict(version=ver, fmt=fmt, d3d=d3d, w=w, h=h, depth=depth, cube=cube,
                stored=stored, full=full, payload=payload, sizes=sizes[:stored],
                smallest_first=smallest_first)


def build_blob(src, name, semantic, category):
    """header | name | pad | loadDef | payload, with offsets the caller fixes up."""
    if src["cube"]:
        raise SystemExit("cubemaps are not supported by this path")
    if src["stored"] == 1:
        flags = 2
    elif src["stored"] != src["full"]:
        raise SystemExit("IWi stores %d of %d levels; the engine can only walk one or all"
                         % (src["stored"], src["full"]))
    else:
        flags = 0

    faces = 1
    needed = 0
    for _ in range(faces):
        for j in range(level_count(flags, src["w"], src["h"], src["depth"])):
            needed += level_bytes(src["d3d"], max(1, src["w"] >> j),
                                  max(1, src["h"] >> j), max(1, src["depth"] >> j))
    if needed != len(src["payload"]):
        raise SystemExit("the engine would read %d bytes but the file holds %d"
                         % (needed, len(src["payload"])))

    nb = name.encode("ascii") + b"\0"
    name_at = 52
    cursor = name_at + len(nb)
    cursor = (cursor + 3) & ~3
    loaddef_at = cursor
    payload_at = loaddef_at + 16
    total = payload_at + len(src["payload"])

    blob = bytearray(total)
    blob[name_at:name_at + len(nb)] = nb
    blob[4] = 3                      # mapType 2D
    blob[5] = semantic
    blob[6] = category
    for i in range(4):               # cardMemory - accounting only
        blob[16 + 4 * i: 20 + 4 * i] = len(src["payload"]).to_bytes(4, "little")
    blob[32:34] = src["w"].to_bytes(2, "little")
    blob[34:36] = src["h"].to_bytes(2, "little")
    blob[36:38] = src["depth"].to_bytes(2, "little")
    blob[38] = 0
    blob[40] = 0

    blob[loaddef_at] = 1 if src["stored"] == 1 else 0
    blob[loaddef_at + 4: loaddef_at + 8] = flags.to_bytes(4, "little")
    blob[loaddef_at + 8: loaddef_at + 12] = src["d3d"].to_bytes(4, "little")
    blob[loaddef_at + 12: loaddef_at + 16] = len(src["payload"]).to_bytes(4, "little")

    if src["smallest_first"]:
        out, read_at = bytearray(), len(src["payload"])
        for i in range(src["stored"]):
            n = iwi_level_bytes(src["fmt"], src["w"] >> i, src["h"] >> i)
            read_at -= n
            out += src["payload"][read_at:read_at + n]
        if read_at != 0 or len(out) != len(src["payload"]):
            raise SystemExit("reversing the mip chain did not consume the payload exactly")
        pixels = bytes(out)
    else:
        pixels = src["payload"]
    blob[payload_at:] = pixels

    return dict(blob=bytes(blob), name_at=name_at, loaddef_at=loaddef_at,
                payload_at=payload_at, flags=flags)


AGENT = r"""
'use strict';
const RENDER_FRAME = ptr(0xBE21F0);
const UPLOAD_RVA   = 0x7E7470;   // sub_BE7470
const LINK_RVA     = 0x09DA10;   // DB_LinkXAssetEntry
const SLOT_RVA     = 0x27C080;   // sub_67C080, current fiber slot
const ENTRIES      = ptr(0x239B120);
const STRIDE       = 28;

let state = null;

rpc.exports.stage = function (spec) {
    const out = { steps: [] };
    const base = Process.findModuleByName('out.exe').base;
    let mallocAddr;
    try { mallocAddr = Process.getModuleByName('msvcrt.dll').getExportByName('malloc'); }
    catch (e) { out.error = 'cannot resolve malloc'; return out; }
    const malloc = new NativeFunction(mallocAddr, 'pointer', ['uint']);

    const bytes = spec.blob;   // array of ints from Python
    const mem = malloc(bytes.length);
    if (mem.isNull()) { out.error = 'malloc failed'; return out; }
    // Write in chunks - a single writeByteArray of ~350KB is fine, but chunking
    // keeps the failure mode readable if it is not.
    const buf = new Uint8Array(bytes).buffer;
    mem.writeByteArray(buf);
    out.storage = mem.toString();
    out.bytes = bytes.length;

    const header = mem;
    const loadDef = mem.add(spec.loaddefAt);
    const namePtr = mem.add(spec.nameAt);
    header.writePointer(loadDef);                       // +0, what sub_BE7470 reads
    header.add(48).writePointer(namePtr);               // +48 name
    out.steps.push('staged ' + bytes.length + ' bytes at ' + mem +
                   '  loadDef ' + loadDef + '  name ' + namePtr);

    state = {
        base: base, header: header, loadDef: loadDef,
        upload: new NativeFunction(base.add(UPLOAD_RVA), 'void', ['pointer', 'pointer']),
        link: new NativeFunction(base.add(LINK_RVA), 'pointer', ['uint32', 'pointer']),
        slotFn: new NativeFunction(base.add(SLOT_RVA), 'uint32', []),
        doUpload: spec.doUpload, doLink: spec.doLink,
        done: false, result: null,
    };
    return out;
};

rpc.exports.run = function () {
    const st = state;
    if (!st) return { error: 'nothing staged' };
    Interceptor.attach(RENDER_FRAME, {
        onEnter: function () {
            if (st.done) return;
            st.done = true;
            const r = { thread: Process.getCurrentThreadId(), steps: [] };
            try { r.fiberSlot = st.slotFn(); } catch (e) { r.fiberSlot = 'threw: ' + e; }
            r.before = {
                at0: '0x' + st.header.readU32().toString(16),
                at2C: '0x' + st.header.add(0x2c).readU32().toString(16),
            };
            if (!st.doUpload) { r.steps.push('UPLOAD SKIPPED (dry run)'); st.result = r; return; }

            try {
                st.upload(st.header, st.header);
                r.steps.push('sub_BE7470 returned');
            } catch (e) { r.error = 'upload threw: ' + e; st.result = r; return; }

            r.after = {
                at0: '0x' + st.header.readU32().toString(16),
                at2C: '0x' + st.header.add(0x2c).readU32().toString(16),
                loadDefRelocated: st.header.add(0x2c).readPointer().equals(st.loadDef),
                category: st.header.add(6).readU8(),
                noPixels: st.header.add(38).readU8(),
            };
            const tex = st.header.readPointer();
            if (tex.isNull()) { r.error = 'no texture was created'; st.result = r; return; }
            try { r.after.textureVtable = tex.readPointer().toString(); } catch (e) {}

            if (!st.doLink) { r.steps.push('LINK SKIPPED'); st.result = r; return; }
            try {
                const slot = Memory.alloc(4);
                slot.writePointer(st.header);
                const entry = st.link(10, slot);
                const published = slot.readPointer();
                r.entry = entry.toString();
                r.published = published.toString();
                if (!entry.isNull() && !published.isNull()) {
                    let same = 0;
                    for (let i = 0; i < 52; i++) {
                        if (published.add(i).readU8() === st.header.add(i).readU8()) same++;
                    }
                    r.headerBytesMatching = same;
                    r.publishedTexture = '0x' + published.readU32().toString(16);
                }
                r.steps.push('DB_LinkXAssetEntry(10) returned ' + entry);
            } catch (e) { r.error = 'link threw: ' + e; }
            st.result = r;
        }
    });
    return { attached: true };
};

rpc.exports.collect = function () {
    Interceptor.detachAll();
    return state ? { done: state.done, result: state.result } : { error: 'nothing staged' };
};

// Independent confirmation: find the name in the XAsset entry table.
rpc.exports.findImage = function (name) {
    for (let i = 1; i < 200000; i++) {
        const e = ENTRIES.add(STRIDE * i);
        let t, h;
        try { t = e.readU32(); h = e.add(8).readPointer(); } catch (err) { break; }
        if (t !== 10 || h.isNull()) continue;
        try {
            const p = h.add(48).readPointer();
            if (p.isNull()) continue;
            let ok = true;
            for (let k = 0; k < name.length; k++) {
                if (p.add(k).readU8() !== name.charCodeAt(k)) { ok = false; break; }
            }
            if (ok && p.add(name.length).readU8() === 0) {
                return {
                    index: i, header: h.toString(),
                    texture: '0x' + h.readU32().toString(16),
                    loadDef: '0x' + h.add(0x2c).readU32().toString(16),
                    width: h.add(32).readU16(), height: h.add(34).readU16(),
                    category: h.add(6).readU8(),
                };
            }
        } catch (err) {}
    }
    return null;
};
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("iwi", type=pathlib.Path)
    ap.add_argument("--name", help="asset name (default: the file stem)")
    ap.add_argument("--semantic", type=int, default=2)
    ap.add_argument("--category", type=int, default=3)
    ap.add_argument("--pid", type=int)
    ap.add_argument("--upload", action="store_true",
                    help="actually call sub_BE7470 on the render thread")
    ap.add_argument("--link", action="store_true",
                    help="also publish with DB_LinkXAssetEntry (implies --upload)")
    ap.add_argument("--seconds", type=float, default=3.0)
    a = ap.parse_args()

    name = a.name or a.iwi.stem
    src = parse_iwi(a.iwi)
    built = build_blob(src, name, a.semantic, a.category)

    print("%s  v%d  %s  %dx%d  %d/%d levels  payload %d"
          % (a.iwi.name, src["version"], IWI_NAME.get(src["fmt"], "?"),
             src["w"], src["h"], src["stored"], src["full"], len(src["payload"])))
    print("  asset name   %s   semantic %d   category %d" % (name, a.semantic, a.category))
    print("  loadDef      flags 0x%x  D3DFORMAT 0x%08x  Levels %d"
          % (built["flags"], src["d3d"], 1 if src["stored"] == 1 else 0))
    print("  blob         %d bytes  (loadDef at %d, payload at %d)"
          % (len(built["blob"]), built["loaddef_at"], built["payload_at"]))
    print("  upload=%s  link=%s" % (a.upload or a.link, a.link))

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

    spec = {
        "blob": list(built["blob"]),
        "nameAt": built["name_at"],
        "loaddefAt": built["loaddef_at"],
        "payloadAt": built["payload_at"],
        "doUpload": bool(a.upload or a.link),
        "doLink": bool(a.link),
    }
    staged = script.exports_sync.stage(spec)
    print()
    print(json.dumps(staged, indent=2))
    if "error" in staged:
        session.detach()
        return 1

    script.exports_sync.run()
    print("waiting up to %.1fs for a render frame ..." % a.seconds)
    deadline = time.time() + a.seconds
    got = None
    while time.time() < deadline:
        time.sleep(0.2)
        got = script.exports_sync.collect()
        if got.get("done"):
            break
    print(json.dumps(got, indent=2))

    if a.link:
        found = script.exports_sync.find_image(name)
        print()
        print("XAsset entry table lookup for %r:" % name)
        print(json.dumps(found, indent=2))
    session.detach()
    return 0 if got and got.get("done") and not (got.get("result") or {}).get("error") else 1


if __name__ == "__main__":
    sys.exit(main())
