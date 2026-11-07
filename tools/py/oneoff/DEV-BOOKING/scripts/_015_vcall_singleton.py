# -*- coding: utf-8 -*-
"""015: find virtual calls on the matching singleton (vtable+disp)."""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_MEM, X86_OP_REG  # noqa

SINGLETON = 0x82E13FC


def main():
    want = set(int(x, 16) for x in sys.argv[1:]) if len(sys.argv) > 1 else None
    pat = struct.pack("<I", SINGLETON)
    i = DATA.find(pat)
    seen = set()
    while i >= 0:
        va = BASE + i
        # containing instruction
        ins0 = None
        for back in range(1, 12):
            st = va - back
            code = DATA[st - BASE: st - BASE + 24]
            ins = next(MD.disasm(code, st), None)
            if ins and ins.address <= va < ins.address + ins.size:
                ins0 = ins
                break
        if ins0 is not None and ins0.mnemonic == "mov" and ins0.operands and \
                ins0.operands[0].type == X86_OP_REG:
            base = ins0.operands[0].reg
            code = DATA[ins0.address - BASE: ins0.address - BASE + 0x60]
            insns = list(MD.disasm(code, ins0.address))[:24]
            tracked = {base}
            for ins in insns[1:]:
                if ins.mnemonic == "mov" and len(ins.operands) == 2 and \
                        ins.operands[0].type == X86_OP_REG and \
                        ins.operands[1].type == X86_OP_REG and \
                        ins.operands[1].reg in tracked:
                    tracked.add(ins.operands[0].reg)
                if ins.mnemonic == "mov" and len(ins.operands) == 2 and \
                        ins.operands[0].type == X86_OP_REG and \
                        ins.operands[1].type == X86_OP_MEM and \
                        ins.operands[1].mem.base in tracked and \
                        ins.operands[1].mem.index == 0:
                    d = ins.operands[1].mem.disp
                    if want is None or d in want:
                        # look for call of this reg within next 4
                        k = insns.index(ins)
                        for nxt in insns[k + 1:k + 10]:
                            if nxt.mnemonic == "call" and \
                                    ins.reg_name(ins.operands[0].reg) in nxt.op_str:
                                key = (ins.address, nxt.address)
                                if key not in seen:
                                    seen.add(key)
                                    print("0x%08X (singleton 0x%08X)  %s %s  ->  call at 0x%08X  [slot +0x%X]"
                                          % (ins.address, ins0.address, ins.mnemonic,
                                             ins.op_str, nxt.address, d))
                                break
                if ins.mnemonic in ("ret", "jmp"):
                    break
        i = DATA.find(pat, i + 1)


if __name__ == "__main__":
    main()
