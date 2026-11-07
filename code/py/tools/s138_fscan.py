#!/usr/bin/env python3
"""s138_fscan: field disp scan including SSE/x87 float stores and 64-bit.
Reports any instruction whose destination memory operand has the given disp,
regardless of value type; classifies as write if dest is memory.
usage: python -I tools\\s138_fscan.py 0x10778 0x10768
"""
import struct
import re
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
CODE_OFF, CODE_SZ = 0x1000, 0x8A7000
WRITE_MN = {"mov", "movzx", "movsx", "add", "sub", "and", "or", "xor", "inc",
            "dec", "shl", "shr", "fst", "fstp", "fadd", "fsub", "fsubr", "fmul",
            "fdiv", "fild", "fistp", "fist", "movss", "movsd", "movaps",
            "movups", "movd", "movq", "fld", "fstcw"}


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


def decode(hit, disp):
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


for arg in sys.argv[1:]:
    if arg.startswith("--"):
        continue
    disp = int(arg, 0)
    print("== disp +0x%X ==" % disp)
    seen = set()
    rows = []
    for h in hits(disp):
        ins = decode(h, disp)
        if not ins or ins.address in seen:
            continue
        seen.add(ins.address)
        rows.append(ins)
    rows.sort(key=lambda i: i.address)
    for ins in rows:
        ops = ins.op_str
        # write if first operand is memory
        first = ops.split(",", 1)[0].strip()
        isw = first.startswith(("dword ptr [", "word ptr [", "byte ptr [",
                                "qword ptr [", "xmmword ptr [")) or \
              (ins.mnemonic.startswith("fst") or ins.mnemonic.startswith("fist"))
        tag = "W" if isw else "r"
        print("  [%s] 0x%08X  %-24s %s %s" % (tag, ins.address, ins.bytes.hex(),
                                               ins.mnemonic, ops))
    print()
