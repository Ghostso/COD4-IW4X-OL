#!/usr/bin/env python3
"""s138_rtti_vt: 给定 RTTI 名字串 VA, 找 TypeDescriptor -> COL -> vtable, 并列出 vtable 槽."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000

def read(va, n=4):
    f = va - VA
    if not (0 <= f <= N - n): return None
    return d[f:f+n]

def u32(va):
    b = read(va, 4)
    return struct.unpack("<I", b)[0] if b else None

def find_ptr(target, limit=24):
    pat = struct.pack("<I", target)
    out = []; i = 0
    while True:
        j = d.find(pat, i)
        if j < 0: break
        out.append(VA + j); i = j + 1
        if len(out) >= limit: break
    return out

def resolve(name_va):
    print("RTTI name @0x%X" % name_va)
    # type descriptor = name_va - 0x10 (vftable + spare + name ptr)  [MSVC: [vfptr][spare][namePtr][...]]
    # search backwards for a u32 == name_va  (that's TypeDescriptor.name ptr)
    cands = [p for p in find_ptr(name_va, 40) if p < name_va and name_va - p < 0x40]
    print("  namePtr refs (TypeDescriptor+0x8?):", ["0x%X" % c for c in cands])
    for c in cands:
        td = c - 8  # TypeDescriptor starts with vfptr(4),spare(4),nameptr(4) => name ptr at td+8
        print("    assume TypeDescriptor @0x%X" % td)
        cols = find_ptr(td, 20)
        print("      COL refs:", ["0x%X" % x for x in cols])
        for col in cols:
            # COL: [signature u32][offset u32][cd u32][td ptr] ; vtable ptr at COL+? -> RTTICompleteObjectLocator
            sig = u32(col)
            off = u32(col + 4)
            cd  = u32(col + 8)
            tdp = u32(col + 12)
            print("        COL @0x%X sig=%s off=%s cd=%s td=%s" % (col, sig, off, cd, hex(tdp) if tdp else None))
            # find pointers to COL -> those are vftable[-1]
            vps = find_ptr(col, 12)
            print("          vftable[-1] refs:", ["0x%X" % v for v in vps])
            for vp in vps:
                vt = vp + 4
                print("            vtable @0x%X:" % vt)
                for k in range(24):
                    fn = u32(vt + 4 * k)
                    if fn is None or not (VA <= fn < VA + N) or fn < 0x401000:
                        break
                    print("              [%2d] 0x%08X" % (k, fn))

if __name__ == "__main__":
    for a in sys.argv[1:]:
        resolve(int(a, 0))
        print()
