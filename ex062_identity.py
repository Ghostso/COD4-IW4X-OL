# EX-062 TASK F/J/Q1: object identity proof across the whole chain, plus
# Task L external boundaries.
import json
from collections import OrderedDict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import X86_REG_ECX, X86_REG_ESI, X86_REG_EBX

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow


LEDGER = """
  SEG 1  allocation
     site        0x12CD3 push 0x1F0 ; 0x12CD8 call sub_2BE34 (operator new)
     returns     EAX = fresh 496-byte block
     EVIDENCE    STATIC_DIRECT (literal size, literal callee)

  SEG 2  constructor
     site        0x12CF0 push eax ; 0x12CF1 call sub_90D0
     arg1        EAX, the SAME value returned by operator new at 0x12CD8
                 (saved to [esp+0x24] at 0x12CE0, pushed at 0x12CF0)
     ctor this   [esp+0x24] of the ctor frame == arg1
     returns     EAX = this (mov eax, ebp at 0x91FF)
     EVIDENCE    STATIC_DIRECT

  SEG 3  return capture
     site        0x12CF6 mov edi, eax
     EVIDENCE    STATIC_DIRECT

  SEG 4  publication
     site        0x12D06 mov [esi+0x19C], edi
     destination ESI = parent object (from 0x12CBD mov esi,[esp+0x18])
     EVIDENCE    STATIC_DIRECT

  SEG 5  retrieval + dispatch
     site        0x12F3C mov ebx, [esp+0x50]     ; parent
                 0x12F40 mov ecx, [ebx+0x19C]      ; SAME slot as 0x12D06
                 0x12F46 mov eax, [ecx]            ; vtable
                 0x12F48 mov edx, [eax+0x50]       ; slot 20
                 0x12F56 call edx                  ; ECX = this
     EVIDENCE    STATIC_DIRECT

  SEG 6  callee this
     site        0x989B mov ebp, ecx
     EVIDENCE    STATIC_DIRECT
"""


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    imp = build_imports(img)

    print("=" * 78)
    print("OBJECT IDENTITY LEDGER")
    print("=" * 78)
    print(LEDGER)

    print("=" * 78)
    print("check: is [parent+0x19C] written anywhere ELSE in iips.dll?")
    print("=" * 78)
    entries = sorted(find_entries(img))
    writes = {}
    reads = {}
    for c in entries:
        b = grow(img, c, md)
        for rva, i in b.items():
            for oi, o in enumerate(i.operands):
                if o.type == X86_OP_MEM and o.mem.disp == 0x19C:
                    rec = (c, "%s %s" % (i.mnemonic, i.op_str))
                    if i.mnemonic in ("mov", "movzx", "movsx") and oi == 0:
                        writes[rva] = rec
                    else:
                        reads[rva] = rec
    print("   WRITES to [..+0x19C]: %d" % len(writes))
    for r in sorted(writes):
        c, t = writes[r]
        tag = "   <== THE PUBLICATION" if r == 0x12D06 else ""
        print("      0x%05X sub_%-8X %s%s" % (r, c, t, tag))
    print("   READS  of [..+0x19C]: %d" % len(reads))
    for r in sorted(reads):
        c, t = reads[r]
        tag = "   <== THE RETRIEVAL" if r == 0x12F40 else ""
        print("      0x%05X sub_%-8X %s%s" % (r, c, t, tag))

    print()
    print("=" * 78)
    print("external API boundaries")
    print("=" * 78)
    print("  allocation helper sub_2BE34:")
    b = grow(img, 0x2BE34, md)
    for rva in sorted(b):
        i = b[rva]
        if i.mnemonic == "call" and i.operands:
            op = i.operands[0]
            if op.type == X86_OP_MEM and op.mem.base == 0:
                print("     0x%05X call %s  -> %s%s" % (
                    rva, i.op_str, imp.get(op.mem.disp - img.base), ""))
            elif op.type == X86_OP_IMM:
                print("     0x%05X call 0x%X (sub_%X)" % (
                    rva, op.imm, op.imm - img.base))
            elif op.type == X86_OP_REG:
                print("     0x%05X call %s (indirect)" % (
                    rva, md.reg_name(op.reg)))

    print()
    print("  initIfsLib externals:")
    fi = grow(img, 0x9570, md)
    for rva, i in sorted(fi.items()):
        if i.mnemonic == "call" and i.operands:
            op = i.operands[0]
            if op.type == X86_OP_MEM and op.mem.base == 0:
                n = imp.get(op.mem.disp - img.base)
                if n and ".dll" in n[0]:
                    print("     0x%05X %s!%s" % (rva, n[0], n[1]))


if __name__ == "__main__":
    main()
