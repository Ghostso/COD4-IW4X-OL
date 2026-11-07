#!/usr/bin/env python3
"""s138_ref2: robust absolute-address xref.
For every 4-byte little-endian occurrence of TGT, try to find an instruction
boundary (start in [hit-10, hit]) such that a decoded instruction both starts
there and covers [hit, hit+4) and references TGT. Report those (alignment-valid).
usage: python -I tools\\s138_ref2.py <hexaddr> [<hexaddr>...]
"""
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def u32(va):
    o = va - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None


def hits(t):
    pat = struct.pack("<I", t)
    r = []
    i = 0
    while True:
        j = d.find(pat, i)
        if j < 0:
            break
        r.append(j)
        i = j + 1
    return r


def valid_ref(hit_file, t):
    ts = "0x%x" % t
    for back in range(0, 9):
        st = hit_file - back
        if st < 0:
            break
        for ins in md.disasm(d[st:st + 16], VA + st):
            if ins.address + ins.size <= VA + hit_file:
                continue
            if ts in ins.op_str.lower() and ins.address <= VA + hit_file:
                return ins
            break
    return None


for arg in sys.argv[1:]:
    t = int(arg, 0)
    hs = hits(t)
    ok = []
    for h in hs:
        ins = valid_ref(h, t)
        if ins:
            ok.append(ins)
    print("== 0x%08X : %d raw byte-hits, %d alignment-valid refs ==" % (t, len(hs), len(ok)))
    for ins in ok:
        print("  0x%08X  %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    print()
