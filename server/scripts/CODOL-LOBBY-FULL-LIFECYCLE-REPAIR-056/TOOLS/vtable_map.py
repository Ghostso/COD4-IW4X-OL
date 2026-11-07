"""Build the class -> vftable -> slot table for the unpacked client image.

All the RTTI/vftable machinery lives in a small VA window (roughly 0xD00000 ..
0xEA59000), so instead of scanning the whole 241 MB image we index just that
window as a dword map -- fast in pure Python, no numpy needed.

Layouts used (verified in this project):
  type_info / TypeDescriptor : TD = name_va - 8 ; TD+4 = pVFTable
  CompleteObjectLocator      : COL+0x0C = pTypeDescriptor ; vftable = COL + 4
  vftable                    : consecutive code pointers, preceded by dword &COL

Usage:
  python -I vtable_map.py <image.bin> <out.json> [--only SUBSTR]
"""
import json
import re
import struct
import sys

BASE = 0x400000
NAME_RE = re.compile(rb"\.\?A[VU][A-Za-z0-9_@?$<>:.\-]{0,400}@@")
ROI_LO, ROI_HI = 0x00C00000, 0x00EA59000      # vftable / COL / TD window
IMG_LO, IMG_HI = 0x00401000, 0x00EA59000      # code pointer plausibility


def main():
    img_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1].lower()

    data = open(img_path, "rb").read()
    size = len(data)
    print("image %s (%d bytes)" % (img_path, size))

    # --- type descriptors ---
    tds = {}
    for m in NAME_RE.finditer(data):
        nm = m.group(0).decode("latin1")
        sva = BASE + m.start()
        td = sva - 8
        off = td - BASE
        if off < 0 or off + 8 > size:
            continue
        pvft = struct.unpack_from("<I", data, off)[0]     # +0 = pVFTable (0x00D77818)
        if IMG_LO <= pvft <= IMG_HI:
            tds[td] = nm
    print("type descriptors: %d" % len(tds))

    # --- dword -> VAs index over the RTTI window ---
    lo_off, hi_off = ROI_LO - BASE, min(ROI_HI - BASE, size)
    idx = {}
    for off in range(lo_off, hi_off - 4, 4):
        v = struct.unpack_from("<I", data, off)[0]
        if v:
            idx.setdefault(v, []).append(BASE + off)
    print("dword index entries: %d" % len(idx))

    # --- COL: a dword holds either the TD VA (classic x86) or the TD RVA
    #     (VS2015+ relative RTTI); COL base = that position - 0x0C ---
    col_of_td = {}
    for td in tds:
        for needle in (td, td - BASE):
            for pos in idx.get(needle, []):
                col = pos - 0x0C
                if col > 0:
                    col_of_td.setdefault(td, set()).add(col)

    # --- vftable: the dword just before the first slot holds &COL (absolute VA) ---
    classes = {}
    for td, cols in col_of_td.items():
        vfts = set()
        for col in cols:
            for pos in idx.get(col, []):
                vfts.add(pos + 4)
        if vfts:
            classes[td] = (tds[td], sorted(vfts))

    print("classes with vftable: %d" % len(classes))

    # --- slots per vftable (stop at the first implausible dword) ---
    out = []
    for td, (nm, vfts) in sorted(classes.items(), key=lambda kv: kv[1][0]):
        if only and only not in nm.lower():
            continue
        for vft in vfts:
            off = vft - BASE
            slots = []
            for i in range(64):
                p = off + i * 4
                if p + 4 > size:
                    break
                fn = struct.unpack_from("<I", data, p)[0]
                if not (IMG_LO <= fn <= IMG_HI):
                    break
                slots.append("0x%08X" % fn)
            out.append({"name": nm, "td": "0x%08X" % td, "vftable": "0x%08X" % vft,
                        "slot_count": len(slots), "slots": slots})

    print("vftables listed: %d" % len(out))
    if only:
        for c in out:
            print("  %-64s vft=%s slots=%d" % (c["name"][:64], c["vftable"], c["slot_count"]))
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"image": img_path, "roi": [hex(ROI_LO), hex(ROI_HI)], "vtables": out},
                      f, indent=1)
        print("wrote %s" % out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
