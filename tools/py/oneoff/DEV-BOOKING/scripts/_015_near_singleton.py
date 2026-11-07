# -*- coding: utf-8 -*-
"""015: near each singleton reference, report lea/writes to [reg+4..0x1C]."""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG  # noqa

SINGLETON = 0x82E13FC
WRITE_MNEM = {"mov", "or", "and", "xor", "add", "sub", "xchg"}
FIELDS = (4, 8, 0xC, 0x10, 0x14, 0x18, 0x1C, 0x20)


def main():
    pat = struct.pack("<I", SINGLETON)
    refs = []
    i = DATA.find(pat)
    while i >= 0:
        refs.append(BASE + i)
        i = DATA.find(pat, i + 1)
    for r in refs:
        ins0 = None
        for back in range(1, 12):
            st = r - back
            code = DATA[st - BASE: st - BASE + 24]
            ins = next(MD.disasm(code, st), None)
            if ins and ins.address <= r < ins.address + ins.size:
                ins0 = ins
                break
        if ins0 is None or not ins0.operands:
            continue
        if ins0.mnemonic not in ("mov", "lea"):
            continue
        if ins0.operands[-1].type != X86_OP_MEM:
            continue
        m0 = ins0.operands[-1].mem
        if m0.disp != SINGLETON or m0.base != 0 or m0.index != 0:
            continue
        if ins0.operands[0].type != X86_OP_REG:
            continue
        reg = ins0.operands[0].reg
        start = ins0.address
        code = DATA[start - BASE: start - BASE + 0x200]
        insns = list(MD.disasm(code, start))
        tracked = {reg}
        for ins in insns[1:]:
            if ins.mnemonic in ("mov", "lea") and ins.operands and \
                    ins.operands[0].type == X86_OP_REG and \
                    ins.operands[-1].type == X86_OP_REG and \
                    ins.operands[-1].reg in tracked and \
                    len(ins.operands) == 2 and ins.mnemonic == "mov":
                tracked.add(ins.operands[0].reg)
            report = False
            if ins.operands and ins.operands[0].type == X86_OP_MEM:
                mm = ins.operands[0].mem
                if mm.base in tracked and mm.index == 0 and mm.disp in FIELDS:
                    if ins.mnemonic == "lea" or (ins.mnemonic in WRITE_MNEM and
                                                 "dword" in ins.op_str):
                        report = True
            if report:
                print("  0x%08X <-singleton 0x%08X   %-22s %s %s"
                      % (ins.address, ins0.address, ins.bytes.hex(),
                         ins.mnemonic, ins.op_str))
            if ins.mnemonic in ("ret", "jmp"):
                break
            if ins.mnemonic == "call" and (not ins.operands or
                                           ins.operands[0].type != X86_OP_MEM):
                # keep scanning through direct calls but stop at indirect
                continue


if __name__ == "__main__":
    main()
