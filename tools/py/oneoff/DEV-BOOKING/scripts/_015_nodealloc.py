# -*- coding: utf-8 -*-
"""015: find nodes linked into [reg+4] right after an allocation call."""
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_MEM, X86_OP_REG  # noqa

WRITE_MNEM = {"mov", "or", "and", "xor", "add", "sub", "xchg"}


def sweep(lo, hi):
    pos = lo
    while pos < hi:
        code = DATA[pos - BASE: min(hi - BASE, pos - BASE + 16)]
        ins = next(MD.disasm(code, pos), None)
        if ins is None or ins.size == 0 or ins.address + ins.size > hi:
            pos += 1
            continue
        yield ins
        pos += ins.size


def main():
    lo = int(sys.argv[1], 16) if len(sys.argv) > 1 else BASE
    hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else END
    winsize = int(sys.argv[3]) if len(sys.argv) > 3 else 0x20
    window = []
    n = 0
    for ins in sweep(lo, hi):
        window.append(ins)
        if len(window) > winsize:
            window.pop(0)
        if not ins.operands or ins.operands[0].type != X86_OP_MEM:
            continue
        m = ins.operands[0].mem
        if m.disp != 4 or m.index != 0 or m.base == 0:
            continue
        if ins.mnemonic not in WRITE_MNEM or "dword" not in ins.op_str:
            continue
        if len(ins.operands) < 2:
            continue
        if ins.operands[1].type != X86_OP_REG:
            continue
        src = ins.operands[1].reg
        # did src come from a call result?
        alloc = None
        for k in range(len(window) - 2, -1, -1):
            b = window[k]
            if b.mnemonic == "call":
                nxt = window[k + 1] if k + 1 < len(window) - 1 else None
                if nxt and nxt.mnemonic == "mov" and nxt.operands[0].type == X86_OP_REG \
                        and nxt.operands[0].reg == src and nxt.operands[1].type == X86_OP_REG:
                    alloc = b
                break
        if alloc is None:
            continue
        # also require a push of a small size before the call
        sz = None
        ki = window.index(alloc)
        for k in range(ki - 1, max(-1, ki - 6), -1):
            b = window[k]
            if b.mnemonic == "push" and b.operands and b.operands[0].type == 2:
                try:
                    sz = int(b.operands[0].imm)
                except Exception:
                    sz = None
                break
        n += 1
        print("---- 0x%08X  %s %s   (node from call 0x%08X, push size=%s)"
              % (ins.address, ins.mnemonic, ins.op_str, alloc.address, sz))
        for b in window[max(0, ki - 4):]:
            print("       0x%08X  %-20s %s %s" % (b.address, b.bytes.hex(),
                                                  b.mnemonic, b.op_str))
            if b.address == ins.address:
                break
    print("total:", n)


if __name__ == "__main__":
    main()
