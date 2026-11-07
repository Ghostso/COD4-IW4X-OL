# -*- coding: utf-8 -*-
"""015: find list-splice idioms writing [reg+4] anywhere in the image."""
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_MEM, X86_OP_REG  # noqa

WRITE_MNEM = {"mov", "or", "and", "xor", "add", "sub", "xchg"}


def sweep(lo, hi):
    pos = lo
    buf = []
    while pos < hi:
        code = DATA[pos - BASE: min(hi - BASE, pos - BASE + 16)]
        ins = next(MD.disasm(code, pos), None)
        if ins is None or ins.size == 0 or ins.address + ins.size > hi:
            pos += 1
            buf = []
            continue
        yield ins, buf
        buf = (buf + [ins])[-6:]
        pos += ins.size


def main():
    lo = int(sys.argv[1], 16) if len(sys.argv) > 1 else BASE
    hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else END
    disp = 4
    n = 0
    for ins, buf in sweep(lo, hi):
        if not ins.operands or ins.operands[0].type != X86_OP_MEM:
            continue
        m = ins.operands[0].mem
        if m.disp != disp or m.index != 0 or m.base == 0:
            continue
        if ins.mnemonic not in WRITE_MNEM or "dword" not in ins.op_str:
            continue
        if len(ins.operands) < 2 or ins.operands[1].type != X86_OP_REG:
            continue
        src = ins.operands[1].reg
        # was src loaded from [something+4] in the recent buffer?
        origin = None
        for b in reversed(buf):
            if b.mnemonic == "mov" and len(b.operands) == 2 and \
                    b.operands[0].type == X86_OP_REG and b.operands[0].reg == src and \
                    b.operands[1].type == X86_OP_MEM and b.operands[1].mem.disp == 4:
                origin = b
                break
        if origin is None:
            continue
        n += 1
        print("---- write 0x%08X  %s %s   (src %s from 0x%08X)"
              % (ins.address, ins.mnemonic, ins.op_str,
                 ins.reg_name(src), origin.address))
        for b in buf:
            print("       0x%08X  %-20s %s %s" % (b.address, b.bytes.hex(),
                                                  b.mnemonic, b.op_str))
        print("       0x%08X  %-20s %s %s   <<<"
              % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    print("total splice candidates:", n)


if __name__ == "__main__":
    main()
