#!/usr/bin/env python3
"""READ-ONLY probe of the client's Direct3D 9 device and the gates on the image
upload path.

Everything a GfxImage publication has to satisfy is a runtime value, and every
one of them is readable without writing anything:

  * dword_11C0E8C   the IDirect3DDevice9. Its BehaviorFlags say whether
                    D3DCREATE_MULTITHREADED (0x4) was set at creation - which is
                    the whole question of whether an upload may be driven from a
                    thread other than the one that made the device.
  * dword_E899CC    a dvar; sub_BE7470 does nothing at all unless +12 is
                    non-zero, and sub_499560 gates a wait loop on the same field.
  * byte_11C0E84    selects the staging path: when set, every image below
                    category 5 is created in SYSTEMMEM and copied across with
                    UpdateTexture instead of being filled in place.

It also reads a shipped image's +0 and +0x2C, because sub_BE7470 RELOCATES the
load definition: the zone stream delivers it at image+0, sub_BE7470 copies it to
image+0x2C and clears +0 for the texture it is about to create. Both offsets
have been called "the load def" in this tree at different times; this prints
both so the pair is unambiguous.

CODREF: sub_BE7470 out.exe 0xBE7470, __cdecl (void **loadDefSlot, GfxImage *).
        sub_487380 (Load_GfxImage) sets dword_1CD1D4C = image before calling it,
        so loadDefSlot IS the image and the field read is image+0.
"""
import sys
import argparse

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


AGENT = r"""
'use strict';
const DEVICE_PTR   = ptr(0x11C0E8C);   // IDirect3DDevice9 *
const STAGING_FLAG = ptr(0x11C0E84);   // byte
const LOAD_DVAR    = ptr(0xE899CC);    // dvar *, +12 read by sub_BE7470
const PICMIP_DVAR  = ptr(0xE89AD0);    // dvar *, +12 read on the category-5 path
const ENTRIES      = ptr(0x239B120);
const STRIDE       = 28;

function imageName(header) {
    try {
        const p = header.add(48).readPointer();
        if (p.isNull()) return null;
        let s = '';
        for (let i = 0; i < 96; i++) {
            const c = p.add(i).readU8();
            if (c === 0) return s.length ? s : null;
            if (c < 32 || c > 126) return null;
            s += String.fromCharCode(c);
        }
        return null;
    } catch (e) { return null; }
}

function dvar(p) {
    const out = { at: p.toString() };
    try {
        const d = p.readPointer();
        out.dvar = d.toString();
        if (d.isNull()) return out;
        out.value = d.add(12).readU32();
        const namePtr = d.readPointer();
        if (!namePtr.isNull()) {
            let s = '';
            for (let i = 0; i < 64; i++) {
                const c = namePtr.add(i).readU8();
                if (c === 0) break;
                if (c < 32 || c > 126) { s = null; break; }
                s += String.fromCharCode(c);
            }
            if (s) out.name = s;
        }
    } catch (e) { out.error = '' + e; }
    return out;
}

rpc.exports.probe = function (sampleCount) {
    const out = { images: [] };

    try { out.stagingFlag = STAGING_FLAG.readU8(); } catch (e) { out.stagingFlag = null; }
    out.loadDvar = dvar(LOAD_DVAR);
    out.picmipDvar = dvar(PICMIP_DVAR);

    // The device, and its creation parameters. GetCreationParameters is vtable
    // index 9 (offset 36) and copies a 20-byte struct; BehaviorFlags is at +16.
    try {
        const dev = DEVICE_PTR.readPointer();
        out.device = dev.toString();
        if (!dev.isNull()) {
            const vt = dev.readPointer();
            out.deviceVtable = vt.toString();
            const fn = new NativeFunction(vt.add(36).readPointer(),
                                          'int32', ['pointer', 'pointer'], 'stdcall');
            const buf = Memory.alloc(32);
            const hr = fn(dev, buf);
            out.getCreationParametersHr = hr;
            if (hr === 0) {
                out.adapterOrdinal = buf.readU32();
                out.deviceType = buf.add(4).readU32();
                out.focusWindow = buf.add(8).readPointer().toString();
                out.behaviorFlags = buf.add(12).readU32();
            }
        }
    } catch (e) { out.deviceError = '' + e; }

    // A handful of shipped images, printing BOTH candidate load-def offsets.
    for (let i = 1; i < 200000 && out.images.length < sampleCount; i++) {
        const e = ENTRIES.add(STRIDE * i);
        let t, h;
        try { t = e.readU32(); h = e.add(8).readPointer(); } catch (err) { break; }
        if (t !== 10 || h.isNull()) continue;
        const n = imageName(h);
        if (n === null) continue;
        const rec = { name: n, header: h.toString() };
        try {
            rec.at0 = h.readU32();
            rec.at2C = h.add(0x2c).readU32();
            rec.mapType = h.add(4).readU8();
            rec.semantic = h.add(5).readU8();
            rec.category = h.add(6).readU8();
            rec.byte7 = h.add(7).readU8();
            rec.byte28 = h.add(0x28).readU8();   // read by sub_4999E0
            rec.byte26 = h.add(0x26).readU8();   // "no pixels" marker
            rec.width = h.add(32).readU16();
            rec.height = h.add(34).readU16();
            rec.depth = h.add(36).readU16();
            if (rec.at0 !== 0) {
                rec.textureVtable = ptr(rec.at0).readPointer().toString();
            }
            if (rec.at2C !== 0) {
                const ld = ptr(rec.at2C);
                rec.loadDef = {
                    levelCount: ld.readU8(),
                    flags: ld.add(4).readU32(),
                    format: ld.add(8).readU32(),
                    resourceSize: ld.add(12).readU32(),
                };
            }
        } catch (err) { rec.error = '' + err; }
        out.images.push(rec);
    }
    return out;
};
"""


def fourcc(v: int) -> str:
    b = v.to_bytes(4, "little")
    if all(32 <= c < 127 for c in b):
        return '"%s"' % b.decode("ascii")
    return str(v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int)
    ap.add_argument("--samples", type=int, default=6)
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
    r = script.exports_sync.probe(a.samples)

    print()
    print("device            %s   vtable %s" % (r.get("device"), r.get("deviceVtable")))
    if "behaviorFlags" in r:
        f = r["behaviorFlags"]
        names = []
        for bit, nm in ((0x00000002, "FPU_PRESERVE"),
                        (0x00000004, "MULTITHREADED"),
                        (0x00000010, "PUREDEVICE"),
                        (0x00000020, "SOFTWARE_VERTEXPROCESSING"),
                        (0x00000040, "HARDWARE_VERTEXPROCESSING"),
                        (0x00000080, "MIXED_VERTEXPROCESSING"),
                        (0x00000100, "DISABLE_DRIVER_MANAGEMENT"),
                        (0x00000800, "ADAPTERGROUP_DEVICE")):
            if f & bit:
                names.append(nm)
        if not (f & 0x00000004):
            names.append("<no MULTITHREADED>")
        print("behaviorFlags     0x%08x  %s" % (f, " | ".join(names) or "-"))
        print("deviceType        %d   adapter %d   focusWindow %s"
              % (r["deviceType"], r["adapterOrdinal"], r["focusWindow"]))
    else:
        print("behaviorFlags     unavailable  %s"
              % (r.get("deviceError") or "hr=%s" % r.get("getCreationParametersHr")))

    for key, label in (("loadDvar", "dword_E899CC (gate)"),
                       ("picmipDvar", "dword_E89AD0 (picmip)")):
        d = r.get(key, {})
        print("%-22s dvar=%s  name=%-24s +12=%s"
              % (label, d.get("dvar"), d.get("name", "?"), d.get("value")))
    print("byte_11C0E84      %s   (staging/UpdateTexture path when non-zero)"
          % r.get("stagingFlag"))

    print()
    print("shipped images - +0 is the texture after upload, +0x2C the load def")
    for im in r["images"]:
        print("  %-32s %s" % (im["name"], im["header"]))
        print("      +0    0x%08x%s" % (
            im["at0"],
            "  vtable " + im["textureVtable"] if "textureVtable" in im else ""))
        print("      +0x2C 0x%08x%s" % (
            im["at2C"],
            ("  levels=%d flags=0x%08x format=%s size=%d" % (
                im["loadDef"]["levelCount"], im["loadDef"]["flags"],
                fourcc(im["loadDef"]["format"]), im["loadDef"]["resourceSize"]))
            if "loadDef" in im else ""))
        print("      mapType=%d semantic=%d category=%d b7=%d  +0x26=%d +0x28=0x%02x"
              "  %dx%dx%d"
              % (im["mapType"], im["semantic"], im["category"], im["byte7"],
                 im["byte26"], im["byte28"], im["width"], im["height"], im["depth"]))
    session.detach()
    return 0


if __name__ == "__main__":
    sys.exit(main())
