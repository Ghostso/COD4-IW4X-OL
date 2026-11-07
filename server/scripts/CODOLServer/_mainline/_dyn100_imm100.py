# -*- coding: utf-8 -*-
"""
_dyn100_imm100.py -- find literal 100 constants in the live image code and
instructions that touch the object used by the lobby-error popup.

Usage:
    python -X utf8 _dyn100_imm100.py <image_best.bin>
"""

import sys

import capstone

MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
MD.detail = True

LO = 0x00400000
CODE_RANGES = [(0x00401000, 0x00994000), (0x00994000, 0x00CA8000)]

TARGET_GLOBALS = {
    "popup_obj_ptr": 0x0849B8AC,
    "popup_state": 0x0849BA34,
    "format_api": 0x00771240,
    "error_route": 0x0076EDF0,
}


def mem_disp(insn):
    vals = []
    for op in insn.operands:
        if op.type == capstone.x86.X86_OP_MEM:
            vals.append(op.mem.disp & 0xFFFFFFFF)
    return vals


def immediate(insn):
    vals = []
    for op in insn.operands:
        if op.type == capstone.x86.X86_OP_IMM:
            vals.append(op.imm & 0xFFFFFFFF)
    return vals


def main():
    path = sys.argv[1]
    with open(path, "rb") as fh:
        b = fh.read()
    print("literal 100 / 0x64 hits in code:")
    count = 0
    for lo, hi in CODE_RANGES:
        for insn in MD.disasm(b[lo - LO:hi - LO], lo):
            if 100 in immediate(insn) or 0x64 in immediate(insn):
                # ignore obvious non-code-looking long ops? print all
                print("  %08X  %-24s %s %s"
                      % (insn.address, insn.bytes.hex(),
                         insn.mnemonic, insn.op_str))
                count += 1
                if count > 300:
                    break
        if count > 300:
            break
    print("total shown: %d" % count)

    print("")
    print("references to the popup object globals / error route:")
    for lo, hi in CODE_RANGES:
        for insn in MD.disasm(b[lo - LO:hi - LO], lo):
            disps = mem_disp(insn)
            for name, g in TARGET_GLOBALS.items():
                if g in disps:
                    print("  %-16s %08X  %-24s %s %s"
                          % (name, insn.address, insn.bytes.hex(),
                             insn.mnemonic, insn.op_str))
                # direct call target
                if insn.mnemonic == "call" and insn.operands:
                    op = insn.operands[0]
                    if op.type == capstone.x86.X86_OP_IMM and (int(op.imm) & 0xFFFFFFFF) == g:
                        print("  %-16s %08X  CALL %s" % (name, insn.address, insn.op_str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
