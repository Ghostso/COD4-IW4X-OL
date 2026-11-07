# -*- coding: utf-8 -*-
"""015: track register holding [0x82e13fc] and find writes to [reg+4]."""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG  # noqa

SINGLETON = 0x82E13FC
WRITE_MNEM = {"mov", "or", "and", "xor", "add", "sub", "xchg"}


def main():
    pat = struct.pack("<I", SINGLETON)
    refs = []
    i = DATA.find(pat)
    while i >= 0:
        refs.append(BASE + i)
        i = DATA.find(pat, i + 1)
    print("refs:", len(refs))
    for r in refs:
        # find instruction containing r
        ins0 = None
        for back in range(1, 12):
            st = r - back
            code = DATA[st - BASE: st - BASE + 24]
            ins = next(MD.disasm(code, st), None)
            if ins and ins.address <= r < ins.address + ins.size:
                ins0 = ins
                break
        if ins0 is None or ins0.mnemonic != "mov" or not ins0.operands:
            continue
        if ins0.operands[1].type != X86_OP_MEM:
            continue
        if ins0.operands[1].mem.disp != SINGLETON or ins0.operands[1].mem.base != 0:
            continue
        if ins0.operands[0].type != X86_OP_REG:
            continue
        reg = ins0.operands[0].reg
        # scan forward in the same function
        start = ins0.address
        code = DATA[start - BASE: start - BASE + 0x300]
        insns = list(MD.disasm(code, start))
        tracked = {reg}
        for ins in insns[1:]:
            if ins.mnemonic == "mov" and ins.operands and \
                    ins.operands[0].type == X86_OP_REG and \
                    ins.operands[1].type == X86_OP_REG and \
                    ins.operands[1].reg in tracked:
                tracked.add(ins.operands[0].reg)
            if ins.mnemonic in WRITE_MNEM and ins.operands and \
                    ins.operands[0].type == X86_OP_MEM and \
                    ins.operands[0].mem.base in tracked and \
                    ins.operands[0].mem.index == 0 and \
                    ins.operands[0].mem.disp in (4, 8, 0xC, 0x10, 0x14, 0x18, 0x1C) \
                    and "dword" in ins.op_str:
                print("  0x%08X (singleton load 0x%08X, reg %s)  %-22s %s %s"
                      % (ins.address, ins0.address, ins0.reg_name(reg),
                         ins.bytes.hex(), ins.mnemonic, ins.op_str))
            if ins.mnemonic in ("ret", "jmp"):
                break
            if ins.mnemonic == "call":
                pass


if __name__ == "__main__":
    main()
