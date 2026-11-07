#!/usr/bin/env python3
"""s138_rtti_resolve: 给定 RTTI 类名字符串的 VA, 反查 TypeDescriptor -> COL -> vftable,
并列出 vftable 的引用点(可能的构造/使用点)。纯静态。
用法: python -I tools/s138_rtti_resolve.py <name_VA_hex> [...]
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read()
N = len(d)
VA = 0x400000
TEXT_LO = 0x401000
TEXT_HI = 0x401000 + 0x8a689a


def u32(off):
    return struct.unpack_from("<I", d, off)[0]


def refs_of(val, lo=0, hi=None):
    hi = hi if hi is not None else N - 4
    pat = struct.pack("<I", val)
    out = []
    i = lo
    while True:
        j = d.find(pat, i, hi)
        if j < 0:
            break
        out.append(j)
        i = j + 1
    return out


def resolve(name_va, quiet=False):
    name_off = name_va - VA
    if not (0 <= name_off < N):
        print("bad name VA")
        return
    # TypeDescriptor: [pVFTable][spare][name]
    for back in (8, 0x10):
        td_va = name_va - back
        hits = refs_of(td_va)
        if hits:
            if not quiet:
                print("  TD VA 0x%08X (name-%d)  refs=%d" % (td_va, back, len(hits)))
            for h in hits:
                # COL layout (x86): signature, offset, cdOffset, pTD, pCHD, pSelf
                sig = u32(h - 0x10) if h >= 0x10 else None
                off_v = u32(h - 0x0C) if h >= 0x0C else None
                cdoff = u32(h - 0x08) if h >= 0x08 else None
                ptype = u32(h - 0x04) if h >= 0x04 else None
                pself = u32(h + 0x04) if h + 4 <= N - 4 else None
                col_va = h - 0x10
                if not quiet:
                    print("    COL@0x%08X sig=%r off=%s cd=%s pTD=0x%08X pSelf=0x%08X"
                          % (col_va, sig, off_v, cdoff, ptype or 0, pself or 0))
                # vftable: COL ptr placed just before vftable
                vhits = refs_of(col_va)
                for v in vhits:
                    vf_va = v + 4
                    slots = []
                    for k in range(6):
                        if vf_va + 4 * k + 4 <= N:
                            slots.append(u32(vf_va - VA + 4 * k))
                    txt = " ".join("0x%08X" % s for s in slots)
                    intext = ["Y" if TEXT_LO <= s < TEXT_HI else "n" for s in slots]
                    if not quiet:
                        print("      vftable@0x%08X  slots: %s  [%s]" %
                              (vf_va, txt, "".join(intext)))
    return


if __name__ == "__main__":
    for a in sys.argv[1:]:
        va = int(a, 0)
        off = va - VA
        e = d.find(b"\x00", off)
        nm = d[off:e][:90].decode("latin1", "replace")
        print("=== %s  VA0x%08X ===" % (nm, va))
        resolve(va)
        print()
