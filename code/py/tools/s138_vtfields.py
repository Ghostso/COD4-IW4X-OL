#!/usr/bin/env python3
"""s138_vtfields: for each vtable slot, disassemble the function (follow direct
flow start only, bounded) and report every instruction that WRITES a field at
[reg + disp] with a constant disp.  Also report reads of named key offsets.

usage: python -I tools\\s138_vtfields.py [--vt 0xdc7274] [--max 0x1200]
Writes are classified and de-duplicated per (slot, disp, width).
"""
import re
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


def code_ptr(v):
    return v is not None and 0x401000 <= v < VA + N


def slots(vt, limit=400):
    r = []
    for i in range(limit):
        p = u32(vt + 4 * i)
        if not code_ptr(p):
            break
        r.append((i, p))
    return r


def func_insns(entry, maxlen=0x2000):
    code = d[entry - VA:entry - VA + maxlen]
    out = []
    for ins in md.disasm(code, entry):
        out.append(ins)
        if ins.mnemonic.startswith("ret"):
            break
        if ins.mnemonic == "int3":
            break
    return out


MEM = re.compile(r"(dword|word|byte|qword) ptr \[[^\]]+\]")


def disp_of(opstr):
    """extract last + 0xNNN or - 0xNNN displacement in the memory operand."""
    m = re.search(r"([+-]) 0x([0-9a-f]+)\]", opstr)
    if not m:
        return None
    v = int(m.group(2), 16)
    return -v if m.group(1) == "-" else v


def width_of(opstr):
    for w in ("dword", "word", "byte", "qword"):
        if w in opstr:
            return w
    return "?"


def analyze(vt):
    sl = slots(vt)
    print("== vtable 0x%08X : %d slots ==" % (vt, len(sl)))
    # per-slot write report
    for idx, fn in sl:
        ins_list = func_insns(fn)
        writes = {}   # disp -> (width, [sites])
        for ins in ins_list:
            ops = ins.op_str
            if not MEM.search(ops):
                continue
            parts = ops.split(",", 1)
            dst = parts[0].strip()
            if not dst.startswith(("dword ptr [", "word ptr [", "byte ptr [", "qword ptr [")):
                continue
            mn = ins.mnemonic
            if mn not in ("mov", "movzx", "movsx", "add", "sub", "and", "or", "xor",
                          "inc", "dec", "shl", "shr", "neg", "not", "imul", "lea"):
                continue
            if mn == "lea":
                continue
            disp = disp_of(dst)
            if disp is None:
                continue
            w = width_of(dst)
            writes.setdefault(disp, []).append((w, ins.address, ins.bytes.hex(), mn, ops))
        if writes:
            print("  slot[%2d] (+0x%03X) fn 0x%08X" % (idx, idx * 4, fn))
            for disp in sorted(writes):
                for w, a, b, mn, ops in writes[disp]:
                    print("      +0x%-6X %-6s 0x%08X %-22s %s %s" % (disp, w, a, b, mn, ops))
    print()


if __name__ == "__main__":
    vt = 0xdc7274
    if "--vt" in sys.argv:
        vt = int(sys.argv[sys.argv.index("--vt") + 1], 0)
    analyze(vt)
