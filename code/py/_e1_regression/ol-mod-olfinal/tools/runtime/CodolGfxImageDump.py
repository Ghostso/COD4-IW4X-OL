#!/usr/bin/env python3
"""READ-ONLY dump of shipped GfxImage assets, and a check of the payload layout.

Calls nothing. Walks the XAsset entry table at 0x239B120 for type 10 and reads
each image's header plus its load definition.

THE OFFSET, SETTLED. This tree has called both +0 and +0x2C "the load def" at
different times, and both readings were half right. `sub_487380` (Load_GfxImage)
sets `dword_1CD1D4C = image` and calls `sub_4872A0`, which fixes up the pointer
at image+0 and then calls `sub_BE7470(image, image)`. That function's first act
is:

    mov edi, [eax]          ; the load def, read from image+0
    mov [esi+2Ch], edi      ; relocated to image+0x2C
    mov dword ptr [esi], 0  ; +0 cleared for the texture it is about to create

So the zone stream delivers the load def at +0, and after load it lives at +0x2C
while +0 holds an IDirect3DTexture9. Reading +0 on a loaded client gets a vtable,
which is what made the earlier reading look convincing.

    GfxImage, 52 bytes            GfxImageLoadDef, 16 bytes + pixels
      +0    IDirect3DTexture9 *     +0   u8  levelCount (0 = full chain)
      +4    u8 mapType 3/4/5        +4   u32 flags   (bit 1 = single mip)
      +5    u8 semantic             +8   u32 format  (a D3DFORMAT or FourCC)
      +6    u8 category             +12  u32 resourceSize (0 = streamed)
      +16   u32 cardMemory[4]       +16  the mip chain, faces outer, levels inner
      +32   u16 width, height, depth
      +38   u8  "no pixels"
      +40   u8  flags read by sub_4999E0
      +44   GfxImageLoadDef *
      +48   const char *name

THE CHECK. `sub_BE7470` walks the payload with two helpers whose arithmetic is
reproduced here exactly:

    sub_BE8C30(flags, w, h, d)  -> level count: 1 if flags & 2, else the full
                                   chain, counted by doubling until it covers
                                   every dimension
    sub_BE8690(format, w, h, d) -> bytes for one level of that format

and the cursor runs faces-outer, levels-inner without resetting between faces.
So every image whose pixels are inline must satisfy

    resourceSize == faces * SUM over levels of sub_BE8690(fmt, w>>j, h>>j, d>>j)

with each dimension clamped at 1. --check runs that over every inline image in
the client and reports how many consume their extent exactly. An emitter that
does not reproduce this arithmetic has no business writing a load def.
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
const STRIDE = 28;

function name(header) {
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

function hex(p, n) {
    let s = '';
    for (let i = 0; i < n; i++) s += p.add(i).readU8().toString(16).padStart(2, '0') + ' ';
    return s.trim();
}

rpc.exports.dump = function (match, limit) {
    const out = { hits: [], all: [], total: 0, withLoadDef: 0, inline: 0 };
    for (let i = 1; i < 200000; i++) {
        const e = ENTRIES.add(STRIDE * i);
        let t, h;
        try { t = e.readU32(); h = e.add(8).readPointer(); } catch (err) { break; }
        if (t !== 10 || h.isNull()) continue;
        out.total++;
        const n = name(h);
        if (n === null) continue;

        let rec;
        try {
            rec = {
                name: n,
                header: h.toString(),
                texture: h.readU32(),
                mapType: h.add(4).readU8(),
                semantic: h.add(5).readU8(),
                category: h.add(6).readU8(),
                width: h.add(32).readU16(),
                height: h.add(34).readU16(),
                depth: h.add(36).readU16(),
                noPixels: h.add(38).readU8(),
                stateByte: h.add(40).readU8(),
                loadDefAt: h.add(0x2c).readU32(),
            };
        } catch (err) { continue; }

        if (rec.loadDefAt !== 0) {
            out.withLoadDef++;
            try {
                const ld = ptr(rec.loadDefAt);
                rec.levelCount = ld.readU8();
                rec.flags = ld.add(4).readU32();
                rec.format = ld.add(8).readU32();
                rec.resourceSize = ld.add(12).readU32();
                if (rec.resourceSize > 0) {
                    out.inline++;
                    rec.dataHex = hex(ld.add(16), 16);
                }
            } catch (err) { rec.loadDefErr = '' + err; }
        }
        out.all.push(rec);
        if (match !== '' && n.indexOf(match) < 0) continue;
        if (out.hits.length >= limit) continue;
        rec.headerHex = hex(h, 52);
        out.hits.push(rec);
    }
    return out;
};
"""


def level_bytes(fmt: int, w: int, h: int, d: int) -> int:
    """sub_BE8690, reproduced exactly."""
    if fmt > 80:
        if fmt > 827611204:
            if fmt in (861165636, 894720068):          # DXT3, DXT5
                return 16 * d * ((h + 3) >> 2) * ((w + 3) >> 2)
        else:
            if fmt == 827611204:                       # DXT1
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


def level_count(flags: int, w: int, h: int, d: int) -> int:
    """sub_BE8C30, reproduced exactly. Only the low byte of flags is read."""
    n = 1
    if (flags & 0xFF) & 2 == 0:
        i = 1
        while i < w or i < h or i < d:
            n += 1
            i *= 2
    return n


def payload_bytes(rec) -> int:
    faces = 6 if rec["mapType"] == 5 else 1
    w, h, d = rec["width"], rec["height"], max(1, rec["depth"])
    levels = level_count(rec["flags"], w, h, d)
    total = 0
    for _ in range(faces):
        for j in range(levels):
            total += level_bytes(rec["format"],
                                 max(1, w >> j), max(1, h >> j), max(1, d >> j))
    return total


def fourcc(v: int) -> str:
    b = v.to_bytes(4, "little")
    if all(32 <= c < 127 for c in b):
        return '"%s"' % b.decode("ascii")
    return str(v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", default="")
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--pid", type=int)
    ap.add_argument("--check", action="store_true",
                    help="verify the payload size formula against every inline image")
    a = ap.parse_args()

    device = frida.get_local_device()
    procs = [q for q in device.enumerate_processes() if q.name.lower() == "out.exe"]
    pid = a.pid or (procs[0].pid if procs else None)
    if pid is None:
        print("no client process found")
        return 2
    session = device.attach(pid)
    script = session.create_script(AGENT)
    script.load()
    r = script.exports_sync.dump(a.match, a.limit)

    print("GfxImage entries: %d   with a load def at +0x2C: %d   pixels inline: %d"
          % (r["total"], r["withLoadDef"], r["inline"]))
    for h in r["hits"]:
        print()
        print("  %s" % h["name"])
        print("    header  %s  %s" % (h["header"], h["headerHex"]))
        print("    %dx%dx%d  mapType=%d semantic=%d category=%d  +38=%d +40=0x%02x"
              "  texture=0x%08x"
              % (h["width"], h["height"], h["depth"], h["mapType"], h["semantic"],
                 h["category"], h["noPixels"], h["stateByte"], h["texture"]))
        if "format" in h:
            print("    loadDef 0x%08x  levelCount=%d flags=0x%08x format=%s"
                  " resourceSize=%d"
                  % (h["loadDefAt"], h["levelCount"], h["flags"],
                     fourcc(h["format"]), h["resourceSize"]))
            if h["resourceSize"]:
                print("    data    %s" % h["dataHex"])
                print("    predicted %d bytes  %s"
                      % (payload_bytes(h),
                         "EXACT" if payload_bytes(h) == h["resourceSize"] else "MISMATCH"))
        else:
            print("    loadDef NULL")

    if a.check:
        inline = [x for x in r["all"] if x.get("resourceSize")]
        exact, wrong = 0, []
        fmts = Counter()
        for x in inline:
            fmts[fourcc(x["format"])] += 1
            if payload_bytes(x) == x["resourceSize"]:
                exact += 1
            else:
                wrong.append(x)
        print()
        print("payload size check over inline images: %d / %d exact"
              % (exact, len(inline)))
        print("formats seen:", dict(fmts.most_common(10)))
        for x in wrong[:12]:
            print("  MISMATCH %-32s %dx%dx%d mapType=%d fmt=%s flags=0x%08x"
                  "  predicted %d  actual %d"
                  % (x["name"], x["width"], x["height"], x["depth"], x["mapType"],
                     fourcc(x["format"]), x["flags"],
                     payload_bytes(x), x["resourceSize"]))
        if wrong and len(wrong) > 12:
            print("  ... and %d more" % (len(wrong) - 12))
    session.detach()
    return 0


if __name__ == "__main__":
    sys.exit(main())
