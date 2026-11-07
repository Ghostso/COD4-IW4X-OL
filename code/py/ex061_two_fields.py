# EX-061: determine whether CNIFS+0x60 in initIfsLib and the pointer used at
# InitInGameApp+0x9A2B/0x9B51/0x9B66/0x9B7B are the SAME object field.
#
# Key question: initIfsLib takes `this` from [esp+0xA0] and InitInGameApp
# passes `push ebp` at 0x99D1.  If the CNIFS object is the same, then
# [this+0x60] is one field with dual use.  Verify by matching the call
# argument.
import json
from collections import OrderedDict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import X86_REG_EBP, X86_REG_ECX, X86_REG_ESP

from ex060_iips_cfg import Image, DLL
from ex060_cfg_engine import Function
from ex061_revalidate import grow


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    fi = Function(img, 0x9570, "initIfsLib").run().build_bbs()
    fn = Function(img, 0x9860, "InitInGameApp").run().build_bbs()

    print("=" * 78)
    print("A. initIfsLib entry: how is `this` obtained?")
    print("=" * 78)
    for rva in sorted(fi.insns):
        if rva > 0x95B0:
            break
        insn = fi.insns[rva]
        print("  0x%05X  %-24s %s %s" % (
            rva, insn.bytes.hex(), insn.mnemonic, insn.op_str))

    print()
    print("  At entry, ECX = this (thiscall). The prologue pushes SEH then")
    print("  `sub esp,0x7c`, pushes ebx/ebp/esi/edi, pushes seh, then")
    print("  `mov ebp,[esp+0xA0]` reads the ORIGINAL ECX?  Check the frame math.")

    print()
    print("=" * 78)
    print("B. InitInGameApp: the call to initIfsLib and its argument")
    print("=" * 78)
    for rva in sorted(fn.insns):
        if 0x99BA <= rva <= 0x99DA:
            insn = fn.insns[rva]
            print("  0x%05X  %-24s %s %s" % (
                rva, insn.bytes.hex(), insn.mnemonic, insn.op_str))

    print()
    print("  ECX for the callee is NOT set here -> initIfsLib is __thiscall")
    print("  via ECX, but ECX at 0x99D2 holds whatever it held before.")
    print("  The explicit `push ebp` is the FIRST STACK ARGUMENT.")

    print()
    print("=" * 78)
    print("C. What is ECX at 0x99D2?  Trace ECX writes in InitInGameApp")
    print("=" * 78)
    last_ecx = None
    for rva in sorted(fn.insns):
        if rva > 0x99D2:
            break
        insn = fn.insns[rva]
        if len(insn.operands) >= 1 and insn.operands[0].type == X86_OP_REG \
                and insn.operands[0].reg == X86_REG_ECX:
            last_ecx = (rva, insn)
            print("  0x%05X  %-24s %s %s" % (
                rva, insn.bytes.hex(), insn.mnemonic, insn.op_str))
    print("  --> last ECX write before the call: 0x%X (%s %s)" % (
        last_ecx[0], last_ecx[1].mnemonic, last_ecx[1].op_str))


if __name__ == "__main__":
    main()
