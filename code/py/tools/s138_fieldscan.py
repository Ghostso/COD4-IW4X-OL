#!/usr/bin/env python3
"""s138_fieldscan: find instructions that write to [reg+disp] for a given disp.
Byte-driven: locate the 4-byte LE displacement inside the code section, then try
decoding an instruction anchored a few bytes before it whose operand contains
'+ 0x<disp>]'. Report only when the instruction actually WRITEs that mem
(mov/and/or/add/etc with dest == mem) — plus any 66 c7 / c7 imm forms.
usage: python -I tools\\s138_fieldscan.py 0x278 [0x105FE ...] [--any]
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
CODE_OFF = 0x1000
CODE_SZ = 0x8A7000


def sec():
    return CODE_OFF, CODE_SZ


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
    if mn in ("mov", "movzx", "movsx", "movsxd"):
        # dest is first operand
        dst = ops.split(",", 1)[0].strip()
        return dst.startswith(("dword ptr [", "word ptr [", "byte ptr ["))
    if mn in ("add", "sub", "and", "or", "xor", "inc", "dec", "shl", "shr", "neg", "not"):
        dst = ops.split(",", 1)[0].strip()
        return dst.startswith(("dword ptr [", "word ptr [", "byte ptr ["))
    return False


for arg in sys.argv[1:]:
    if arg.startswith("--"):
        continue
    disp = int(arg, 0)
    print("== disp +0x%X ==" % disp)
    seen = set()
    rows = []
    for h in hits(disp):
        ins = try_decode(h, disp)
        if not ins or ins.address in seen:
            continue
        seen.add(ins.address)
        if is_write(ins):
            rows.append(ins)
    rows.sort(key=lambda i: i.address)
    for ins in rows:
        print("  0x%08X  %-26s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    print("  %d write-sites" % len(rows))
    print()
