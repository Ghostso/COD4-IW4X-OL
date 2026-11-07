# EX-060 TASK 1: parameter provenance + shared/global state for
# CNIFS::initIfsLib (0x9570) and CNIFS::InitInGameApp (0x9860).
import os
import re
import struct
from collections import OrderedDict, defaultdict

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex060_cfg_engine import Function, COND_JMP

DAT = None


def collect_globals(img, fn, lo, hi):
    """Find absolute memory operands inside [lo,hi) within the function."""
    out = defaultdict(list)
    for rva, insn in fn.insns.items():
        if not (lo <= rva <= hi):
            continue
        for op in insn.operands:
            if op.type == X86_OP_MEM and op.mem.base == 0 and op.mem.index == 0:
                va = op.mem.disp
                out[va].append((rva, "%s %s" % (insn.mnemonic, insn.op_str)))
    return out


def mem_access(s):
    """Classify a memory operand as READ / WRITE for a simple instruction."""
    return s


def main():
    img = Image(DLL)
    imports = build_imports(img)
    base = img.base
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    print("iips.dll base 0x%X size 0x%X" % (base, img.size))

    # ---- TASK 3: search entire iips.dll for absolute references in
    # [0x80000000, 0x90000000) -- the range that contains 0x8189FEC.
    print()
    print("=" * 74)
    print("TASK 3 : absolute memory operands in iips.dll whose displacement")
    print("         lies in [0x80000000, 0x90000000)  (target class of 8189FEC)")
    print("=" * 74)
    found = []
    for rva in range(0x1000, 0x33000):
        if not img.is_code(rva):
            continue
        for insn in md.disasm(img.read(rva, 15), base + rva):
            for op in insn.operands:
                if op.type == X86_OP_MEM:
                    d = op.mem.disp
                    if 0x80000000 <= d < 0x90000000:
                        found.append((rva, insn, d))
            break
    if not found:
        print("  NO absolute memory operand into 0x80000000..0x90000000")
    for rva, insn, d in found:
        print("  +0x%X  %s %s  (disp 0x%X)" % (rva, insn.mnemonic, insn.op_str, d))

    # ---- Also search immediates in that range
    print()
    print("immediates in [0x80000000,0x90000000):")
    found = []
    for rva in range(0x1000, 0x33000):
        if not img.is_code(rva):
            continue
        for insn in md.disasm(img.read(rva, 15), base + rva):
            for op in insn.operands:
                if op.type == X86_OP_IMM and 0x80000000 <= op.imm < 0x90000000:
                    found.append((rva, insn))
            break
    if not found:
        print("  NONE")
    for rva, insn in found:
        print("  +0x%X  %s %s" % (rva, insn.mnemonic, insn.op_str))

    # ---- TASK 1: global/static state touched by the two functions
    print()
    print("=" * 74)
    print("TASK 1 : global/static state in initIfsLib (0x9570..0x9860)")
    print("=" * 74)
    f = Function(img, 0x9570, "initIfsLib").run().build_bbs()
    g = collect_globals(img, f, 0x9570, 0x9860)
    for va, sites in sorted(g.items()):
        print("  global 0x%08X : %d sites" % (va, len(sites)))
        for rva, txt in sites:
            print("      +0x%X  %s" % (rva, txt))

    print()
    print("=" * 74)
    print("TASK 1 : global/static state in InitInGameApp (0x9860..0xA833)")
    print("=" * 74)
    g2 = Function(img, 0x9860, "InitInGameApp").run().build_bbs()
    gg = collect_globals(img, g2, 0x9860, 0xA833)
    for va, sites in sorted(gg.items()):
        print("  global 0x%08X : %d sites" % (va, len(sites)))
        for rva, txt in sites[:6]:
            print("      +0x%X  %s" % (rva, txt))
        if len(sites) > 6:
            print("      ... (%d more)" % (len(sites) - 6))


if __name__ == "__main__":
    main()
