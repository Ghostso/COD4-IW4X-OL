# -*- coding: utf-8 -*-
"""BA-08 vftable 边界定位器.

MSVC x86: vftable 之前 4 字节 = COL 指针 (通常 COL 的 RVA).
一个类的 vftable 可能被拆成多段 (多重继承/ICF).
本工具: 给定 TD, 找出所有"前导槽 == COL 指针"的 vftable 起点.
"""
import re
import struct
import sys

IMG = r"E:\codol_re\client_image_20261027.bin"
BASE = 0x400000
d = open(IMG, "rb").read()
N = len(d)


def u4(o):
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None


def cstr(off, mx=400):
    e = d.find(b"\x00", off, min(off + mx, N))
    return d[off:e].decode("latin1", "replace") if e > 0 else ""


def td_at(td_rva):
    return cstr(td_rva + 8, 300)


def find_cols(td_rva):
    out = []
    for target in (td_rva, td_rva + BASE):
        pat = struct.pack("<I", target)
        i = d.find(pat)
        while i >= 0:
            col = i - 12
            if col >= 0 and u4(col) == 0:
                out.append(col)
            i = d.find(pat, i + 1)
    return out


def find_vftables(col):
    """vftable 起点: 某处 4 字节 == col (RVA) 或 col+BASE (VA)."""
    out = []
    for target in (col, col + BASE):
        pat = struct.pack("<I", target)
        i = d.find(pat)
        while i >= 0:
            out.append(i + 4)
            i = d.find(pat, i + 1)
    return out


def count_slots(vt):
    n = 0
    p = vt
    while p + 4 <= N:
        v = u4(p)
        if v and BASE + 0x1000 <= v < BASE + N:
            n += 1
            p += 4
        else:
            break
        if n > 400:
            break
    return n


def main():
    if len(sys.argv) < 2:
        print("usage: ba08_vftable.py <td_rva_hex> [...]")
        return
    for a in sys.argv[1:]:
        td = int(a, 16)
        print("=" * 80)
        print("TD 0x%08X  %s" % (td, td_at(td)))
        cols = find_cols(td)
        print("  COL: %d -> %s" % (len(cols), [hex(c) for c in cols]))
        for col in cols:
            sig, off, cd, tdf, chd = struct.unpack_from("<IIIII", d, col)
            print("  COL 0x%08X  sig=0x%X offset=0x%X cd=0x%X td=0x%X chd=0x%X"
                  % (col, sig, off, cd, tdf, chd))
            if chd:
                print("    CHD 0x%08X: %s" % (chd, d[chd:chd + 32].hex(" ")))
            vts = find_vftables(col)
            print("    vftable 候选 %d 个:" % len(vts))
            for vt in vts:
                n = count_slots(vt)
                # 抽样前几个槽
                sl = [u4(vt + i * 4) for i in range(min(4, n))]
                print("      RVA 0x%08X  %3d 槽  前4: %s"
                      % (vt, n, " ".join("0x%08X" % x for x in sl)))


if __name__ == "__main__":
    main()
