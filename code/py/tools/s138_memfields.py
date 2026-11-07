#!/usr/bin/env python3
"""s138_memfields: like fieldscan but for a disp AND restricted to an address
range [start,end); also resolves the member-record base (0x1D0 stride patterns).
usage: python -I tools\\s138_memfields.py 0x88 0x90 0xAC --lo 0x620000 --hi 0x640000
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
CODE_OFF, CODE_SZ = 0x1000, 0x8A7000


def hits(disp):
    pat = struct.pack("<I", disp)
    seg = d[CODE_OFF:CODE_OFF + CODE_SZ]
    r = []
    i = 0
    while True:
        j = seg.find(pat, i)
        if j < 0:
            break
        r.append(CODE_OFF + j)
        i = j + 1
    return r


def try_decode(hit, disp):
    ts = "+ 0x%x]" % disp
    for back in range(2, 9):
        st = hit - back
        if st < 0:
            continue
        got = list(md.disasm(d[st:st + 16], VA + st))
        if not got:
            continue
        ins = got[0]
        if ins.address + ins.size <= VA + hit:
            continue
        if ts in ins.op_str.lower():
            return ins
    return None


def is_write(ins):
    mn, ops = ins.mnemonic, ins.op_str
    if mn in ("mov", "movzx", "movsx", "movsxd", "add", "sub", "and", "or",
              "xor", "inc", "dec", "shl", "shr"):
        dst = ops.split(",", 1)[0].strip()
        return dst.startswith(("dword ptr [", "word ptr [", "byte ptr ["))
    return False


lo, hi = 0, 0x20000000
args = []
for i, a in enumerate(sys.argv[1:]):
    if a == "--lo":
        lo = int(sys.argv[i + 2], 0)
    elif a == "--hi":
        hi = int(sys.argv[i + 2], 0)
    elif not a.startswith("--") and (i == 0 or sys.argv[i - 1] not in ("--lo", "--hi")):
        args.append(a)

for arg in args:
    disp = int(arg, 0)
    print("== disp +0x%X  range [0x%X,0x%X) ==" % (disp, lo, hi))
    seen = set()
    rows = []
    for h in hits(disp):
        ins = try_decode(h, disp)
        if not ins or ins.address in seen:
            continue
        seen.add(ins.address)
        if lo <= ins.address < hi and is_write(ins):
            rows.append(ins)
    rows.sort(key=lambda i: i.address)
    for ins in rows:
        print("  0x%08X  %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    print("  %d write-sites" % len(rows))
    print()
