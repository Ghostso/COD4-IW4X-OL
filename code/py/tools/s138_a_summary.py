#!/usr/bin/env python3
"""s138_a_summary: for every opcode in the 76-entry table (and the 0x3E9/0x3EA..0x3F2
extension tables), resolve target -> executor -> the vt[slot] taken on [+0x4F0]
and, via the static singleton vtable 0xDE07A4, the concrete function.
Usage: python -I tools/s138_a_summary.py
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


def dis(va, n=0x80):
    return list(md.disasm(d[va - VA:va - VA + n], va))


def analyze(target):
    """Return (executor, slot, concrete) walking the branch at target."""
    ins = dis(target, 0x60)
    exe = None
    slot = None
    for i, x in enumerate(ins):
        if x.mnemonic == "call" and x.op_str.startswith("0x"):
            exe = int(x.op_str, 16)
            break
    if exe:
        # disassemble executor head to find vt slot
        for y in dis(exe, 0xA0):
            if y.mnemonic == "mov" and "+ 0x" in y.op_str and "[edx" in y.op_str:
                try:
                    slot = int(y.op_str.split("+")[1].strip("] "), 16)
                except ValueError:
                    pass
                break
    concrete = None
    if slot is not None:
        concrete = u32(0xDE07A4 + slot)
    return exe, slot, concrete


def table(base, n, idx0):
    out = []
    for k in range(n):
        t = u32(base + 4 * k)
        out.append((idx0 + k, t))
    return out


print("opcode | branch | executor | vt[slot] | concrete")
rows = []
rows += table(0xB83744, 0x4B, 1)
rows.append((0x3E9, 0xB83547))
for k, t in table(0xB83870, 9, 0x3EA):
    rows.append((k, t))
for op, t in rows:
    exe, slot, conc = analyze(t)
    print("0x%02X (%3d) | 0x%08X | %s | %s | %s"
          % (op, op, t, ("0x%08X" % exe) if exe else "-",
             ("0x%02X" % slot) if slot is not None else "-",
             ("0x%08X" % conc) if conc else "-"))
