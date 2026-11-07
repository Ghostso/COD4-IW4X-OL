# EX-061 TASK 7: determine `this` provenance for every +0x60 site and
# separate genuine CNIFS accesses from merely-coincidental +0x60 fields on
# other object types.
import json
from collections import OrderedDict, defaultdict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import (
    X86_REG_EBP, X86_REG_ECX, X86_REG_ESI, X86_REG_EDI, X86_REG_EBX,
    X86_REG_EAX, X86_REG_EDX, X86_REG_ESP,
)

from ex060_iips_cfg import Image, DLL, build_imports
from ex060_cfg_engine import Function

from ex061_owners import main as _unused  # noqa
from ex061_revalidate import find_entries, grow
from ex061_functions import code_bounds


def fn_body(img, md, entry):
    return grow(img, entry, md)


def trace_ebp_source(body, md, up_to_rva):
    """Return the instruction that set EBP for the frame, if it is a frame
    pointer (push ebp / mov ebp,esp) or a `this` load."""
    # Find the last write to ebp before up_to_rva.
    last = None
    for rva in sorted(body):
        if rva > up_to_rva:
            break
        insn = body[rva]
        if insn.mnemonic == "mov" and len(insn.operands) == 2:
            dst, src = insn.operands
            if dst.type == X86_OP_REG and dst.reg == X86_REG_EBP:
                last = (rva, insn)
    return last


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    imports = build_imports(img)

    # The two CNIFS functions
    fns = {
        "CNIFS::InitInGameApp": 0x9860,
        "CNIFS::initIfsLib": 0x9570,
    }

    print("=" * 78)
    print("A. `this` provenance inside the two CNIFS functions")
    print("=" * 78)
    for name, entry in fns.items():
        body = fn_body(img, md, entry)
        print()
        print("-- %s (0x%X), %d insns" % (name, entry, len(body)))
        # Find the this-load
        for rva in sorted(body):
            insn = body[rva]
            if rva > entry + 0x120:
                break
            if insn.mnemonic == "mov" and len(insn.operands) == 2:
                dst, src = insn.operands
                # mov ebp, ecx  -> this
                if (dst.type == X86_OP_REG and dst.reg == X86_REG_EBP
                        and src.type == X86_OP_REG and src.reg == X86_REG_ECX):
                    print("   0x%X  mov ebp, ecx            <== this loaded from ECX"
                          % rva)
                # mov ebp, [esp+0xA0] -> this from stack
                if (dst.type == X86_OP_REG and dst.reg == X86_REG_EBP
                        and src.type == X86_OP_MEM
                        and src.mem.base == X86_REG_ESP):
                    print("   0x%X  mov ebp, [esp+0x%X]    <== this loaded from stack"
                          % (rva, src.mem.disp))
        # show the +0x60 sites with the instruction
        print("   +0x60 sites:")
        for rva in sorted(body):
            insn = body[rva]
            for op in insn.operands:
                if (op.type == X86_OP_MEM and op.mem.disp == 0x60
                        and op.mem.base == X86_REG_EBP):
                    print("     0x%X  %-24s %s %s" % (
                        rva, insn.bytes.hex(), insn.mnemonic, insn.op_str))

    print()
    print("=" * 78)
    print("B. other functions with [reg+0x60] -- object type check")
    print("=" * 78)
    others = {
        "sub_90D0": 0x90D0,
        "sub_9240": 0x9240,
        "sub_A860": 0xA860,
        "sub_15A00": 0x15A00,
    }
    for name, entry in others.items():
        body = fn_body(img, md, entry)
        print()
        print("-- %s (0x%X), %d insns" % (name, entry, len(body)))
        # what base register, and is it edx/ecx (member fn) or a local?
        for rva in sorted(body):
            insn = body[rva]
            for op in insn.operands:
                if op.type == X86_OP_MEM and op.mem.disp == 0x60:
                    print("     0x%X  %-24s %s %s" % (
                        rva, insn.bytes.hex(), insn.mnemonic, insn.op_str))


if __name__ == "__main__":
    main()
