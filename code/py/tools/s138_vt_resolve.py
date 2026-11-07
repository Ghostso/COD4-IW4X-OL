#!/usr/bin/env python3
"""s138_vt_resolve: name -> vtable 通过 MSVC RTTI, 输出 COL 槽和 vtable 槽(带邻近字符串注释)."""
import struct, sys, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)

def u32(va):
    o = va - VA
    if 0 <= o <= N - 4: return struct.unpack_from("<I", d, o)[0]
    return None

def cstr(va, ml=120):
    o = va - VA
    if not (0 <= o < N - 1): return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 2: return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None

def ptrs(v, lim=30):
    pat = struct.pack("<I", v); o = []; i = 0
    while True:
        j = d.find(pat, i)
        if j < 0: break
        o.append(VA + j); i = j + 1
        if len(o) >= lim: break
    return o

def ti_of(nm):
    i = d.find(nm.encode())
    return (i + VA) - 8 if i >= 0 else None

def resolve_class_name(nm, show_slots=30):
    ti = ti_of(nm)
    print("### %s  ti=0x%X" % (nm, ti or 0))
    if not ti: return
    for pref in ptrs(ti, 12):
        col = pref - 0xC
        sig = u32(col)
        off = u32(col + 4)
        td = u32(col + 12)
        if td != ti: continue
        if sig not in (0, 1): continue
        print("  COL 0x%X sig=%d off=%d" % (col, sig, off))
        for colp in ptrs(col, 8):
            vt = colp + 4
            if u32(colp) != col: continue
            print("    vtable @0x%X (vftable[-1]=0x%X)" % (vt, colp))
            for k in range(show_slots):
                fn = u32(vt + 4 * k)
                if not fn or not (0x401000 <= fn < 0x401000 + 0x8a689a):
                    break
                note = ""
                # annotate first few bytes call target / strings
                print("      [%2d] 0x%08X" % (k, fn))

if __name__ == "__main__":
    for nm in sys.argv[1:]:
        resolve_class_name(nm)
        print()
