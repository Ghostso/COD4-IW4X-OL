"""Extract MSVC RTTI class names + type descriptors from the unpacked client image.

Input: the image carved by extract_image_from_dump.py (VA - 0x400000 = offset).

MSVC 32-bit RTTI layout we rely on:
  TypeDescriptor  : +0x00 vftable ptr, +0x04 spare, +0x08 name (char*, VA),
                    +0x0C name length, then the decorated name (" .?AV..." )
  CompleteObjectLocator (COL): at vftable-4 points to a COL whose +0x0C is the
                    TypeDescriptor VA.  Signed/unsigned field at +0x10/+0x14.

This tool reports, per class name:
  name, TypeDescriptor VA, and every vftable VA that references the COL which
  points at that TypeDescriptor.

Usage:
  python -I rtti_inventory.py <image.bin> [out.json]
"""
import json
import os
import re
import struct
import sys

BASE = 0x400000
NAME_RE = re.compile(rb"\.\?A[VU][A-Za-z0-9_@?$<>:.\-]{0,400}@@")


def main():
    img_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    data = open(img_path, "rb").read()
    size = len(data)
    print("image %s (%d bytes, VA 0x%X..0x%X)" % (img_path, size, BASE, BASE + size))

    # 1) type descriptor names: the name string is stored right after a
    #    TypeDescriptor header, so the VA stored at header+0x08 points at the
    #    string.  Collect candidate (string_va -> name).
    names = {}
    for m in NAME_RE.finditer(data):
        s = m.group(0)
        if len(s) < 8:
            continue
        names[BASE + m.start()] = s.decode("latin1")

    # 2) type descriptors.  MSVC x86 type_info layout:
    #      +0x00 vftable ptr (points at the shared type_info vftable)
    #      +0x04 spare (_M_data, usually 0)
    #      +0x08 the decorated name, stored INLINE
    #    so TD = name_va - 8.
    tds = {}
    vf_ptr_hist = {}
    for sva, nm in names.items():
        td = sva - 8
        off = td - BASE
        if off < 0 or off + 8 > size:
            continue
        vft, spare = struct.unpack_from("<II", data, off)
        if not (BASE <= vft < BASE + size):
            continue
        vf_ptr_hist[vft] = vf_ptr_hist.get(vft, 0) + 1
        tds[td] = nm
    print("type descriptors: %d" % len(tds))
    if vf_ptr_hist:
        top = sorted(vf_ptr_hist.items(), key=lambda kv: -kv[1])[:3]
        print("  type_info vftable candidates: " +
              ", ".join("0x%08X x%d" % (v, c) for v, c in top))

    # 3) vftables: a COL sits 4 bytes before a vftable; COL+0x0C == TD VA.
    #    Walk every 4-byte aligned dword in .rdata-ish space, treat it as a
    #    candidate COL VA, read COL+0x0C, and if that is a known TD, look for
    #    dwords equal to (col_va + 4) elsewhere (those are the vftables).
    col_to_td = {}
    for off in range(0, size - 0x20, 4):
        v = struct.unpack_from("<I", data, off)[0]
        if v in tds:
            col_va = BASE + off - 0x0C
            if col_va >= BASE:
                col_to_td[col_va] = v
    print("candidate COLs: %d" % len(col_to_td))

    # index: dword value -> offsets where it appears (vftable refs are the
    # dword "COL VA + 4" appearing once, typically in .rdata)
    want = {}
    for col_va, td in col_to_td.items():
        want[struct.pack("<I", col_va + 4)] = td
    vft_of = {}
    for needle, td in want.items():
        start = 0
        while True:
            i = data.find(needle, start)
            if i < 0:
                break
            vft_of.setdefault(td, []).append(BASE + i + 4)
            start = i + 1

    classes = []
    for td, nm in sorted(tds.items(), key=lambda kv: kv[1]):
        classes.append({
            "name": nm,
            "type_descriptor_va": "0x%08X" % td,
            "vftables": ["0x%08X" % v for v in sorted(set(vft_of.get(td, [])))],
        })
    with_vft = [c for c in classes if c["vftables"]]
    print("classes with vftable: %d / %d" % (len(with_vft), len(classes)))

    # quick lobby-relevant census
    keys = ("dwRoom", "Room", "Match", "Lobby", "Session", "Demonware", "Lsg",
            "EventHandler", "Party", "LobbyMatch", "Connection", "NetChan")
    print("\n--- classes matching lobby keywords (name / vftable) ---")
    for c in with_vft:
        if any(k.lower() in c["name"].lower() for k in keys):
            print("  %-70s td=%s vft=%s" % (c["name"][:70], c["type_descriptor_va"],
                                            ",".join(c["vftables"][:4])))

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"image": img_path, "classes": classes}, f, indent=1)
        print("\nwrote %s (%d classes)" % (out_path, len(classes)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
