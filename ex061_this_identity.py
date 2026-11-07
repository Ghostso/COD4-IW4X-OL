# EX-061 TASK 7: object-instance disambiguation.
#
# Several functions access [<base>+0x60].  They are only the SAME CNIFS field
# if their object pointer is the same CNIFS instance.  Determine each
# function's `this`-provenance and its callers.
import json
from collections import OrderedDict, defaultdict, deque

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import X86_REG_EBP, X86_REG_ECX, X86_REG_ESP

from ex060_iips_cfg import Image, DLL, build_imports
from ex060_cfg_engine import Function, COND_JMP
from ex061_revalidate import find_entries, grow


def callers_of(img, md, entries, target):
    """Find all call sites in the image that target `target`."""
    out = []
    for c in entries:
        body = grow(img, c, md)
        for rva, insn in body.items():
            if insn.mnemonic == "call" and insn.operands:
                op = insn.operands[0]
                if op.type == X86_OP_IMM and op.imm - img.base == target:
                    out.append((c, rva))
    return out


def this_provenance(img, md, entry, body):
    """Report how the function obtains its object pointer."""
    notes = []
    for rva in sorted(body):
        if rva > entry + 0x80:
            break
        insn = body[rva]
        if insn.mnemonic == "mov" and len(insn.operands) == 2:
            d, s = insn.operands
            if d.type == X86_OP_REG and md.reg_name(d.reg) in ("ebp", "esi", "edi", "ebx"):
                if s.type == X86_OP_REG:
                    notes.append((rva, "reg %s = %s" % (
                        md.reg_name(d.reg), md.reg_name(s.reg))))
                elif s.type == X86_OP_MEM:
                    notes.append((rva, "%s = [%s+0x%X]" % (
                        md.reg_name(d.reg),
                        md.reg_name(s.mem.base) if s.mem.base else "abs",
                        s.mem.disp)))
    return notes


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    entries = sorted(find_entries(img))

    targets = {
        "initIfsLib(0x9570)": 0x9570,
        "InitInGameApp(0x9860)": 0x9860,
        "sub_90D0": 0x90D0,
        "sub_9240": 0x9240,
        "sub_A860": 0xA860,
        "sub_135B0": 0x135B0,
        "sub_15A00": 0x15A00,
        "sub_2E310": 0x2E310,
    }

    print("=" * 78)
    print("object-pointer provenance per function")
    print("=" * 78)
    for name, entry in targets.items():
        body = grow(img, entry, md)
        print()
        print("-- %s  body 0x%X..0x%X  (%d insns)" % (
            name, entry, max(body.keys()), len(body)))
        for rva, note in this_provenance(img, md, entry, body)[:6]:
            print("     0x%05X  %s" % (rva, note))

    print()
    print("=" * 78)
    print("callers of the two CNIFS functions (immediate call targets)")
    print("=" * 78)
    for name, entry in (("initIfsLib", 0x9570), ("InitInGameApp", 0x9860)):
        cs_ = callers_of(img, md, entries, entry)
        print("  %s : %d immediate callers" % (name, len(cs_)))
        for owner, rva in cs_[:20]:
            print("      from sub_%X at 0x%X" % (owner, rva))


if __name__ == "__main__":
    main()
