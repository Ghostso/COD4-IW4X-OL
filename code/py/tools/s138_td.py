#!/usr/bin/env python3
"""s138_td: TypeDescriptor/COL/vtable resolver (fixed).
MSVC layout: COL = [sig u32][offset u32][cdOffset u32][pTD u32][pCHD u32](x64 only has ..).
x86 (32-bit) RTTICompleteObjectLocator: {signature, offset, cdOffset, pTypeDescriptor, pClassDescriptor}
So the pointer-to-TD sits at COL+0xC.  COL start = (ptr_to_td) - 0xC.
vftable's [-1] slot holds the COL address => vtable = (addr holding COL) + 4.
Usage: s138_td.py <substring>...
"""
import re, struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000


def u32(va):
    f = va - VA
    return struct.unpack_from("<I", d, f)[0] if 0 <= f <= N - 4 else None


def find_ptr(target, limit=64):
    pat = struct.pack("<I", target); out = []; i = 0
    while True:
        j = d.find(pat, i)
        if j < 0: break
        out.append(VA + j); i = j + 1
        if len(out) >= limit: break
    return out


def cstr(va, ml=200):
    f = va - VA
    if not (0 <= f < N - 1): return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > ml: return None
    s = d[f:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


def show(pat):
    print("\n############ %r" % pat)
    b = b".?AV" + pat.encode()
    m = re.search(re.escape(b), d)
    if not m:
        print("   no name")
        return
    name_va = VA + m.start()
    print("   name @0x%08X = %r" % (name_va, cstr(name_va)))
    td = name_va - 8
    print("   TD @0x%08X" % td)
    for p in find_ptr(td, 16):
        col = p - 0xC
        sig = u32(col); off = u32(col + 4); cd = u32(col + 8); tdp = u32(col + 12)
        print("   COL @0x%08X sig=0x%X off=%s cd=%s pTD=0x%08X" % (col, sig or 0, off, cd, tdp or 0))
        if sig not in (0, 1):
            print("      (signature invalid, skip)")
            continue
        for vp in find_ptr(col, 16):
            vt = vp + 4
            print("       vtable @0x%08X" % vt)
            i = 0
            while i < 60:
                s = u32(vt + 4 * i)
                if s is None or not (0x401000 <= s < VA + N):
                    break
                print("         slot[%2d] 0x%08X" % (i, s))
                i += 1


for pat in sys.argv[1:]:
    show(pat)
