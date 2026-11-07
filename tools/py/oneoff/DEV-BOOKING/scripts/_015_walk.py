# -*- coding: utf-8 -*-
"""015: find "walk list of [X+4] and virtual-dispatch" loops anywhere in image."""
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_MEM, X86_OP_REG  # noqa


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
        yield ins
        pos += ins.size


def is_mov_load(ins, disp=None):
    """mov reg, dword ptr [reg(+disp)]"""
    if ins.mnemonic != "mov" or len(ins.operands) != 2:
        return None
    if ins.operands[0].type != X86_OP_REG or ins.operands[1].type != X86_OP_MEM:
        return None
    m = ins.operands[1].mem
    if m.index != 0 or m.base == 0:
        return None
    if disp is not None and m.disp != disp:
        return None
    return ins.operands[0].reg, m


def main():
    lo = int(sys.argv[1], 16) if len(sys.argv) > 1 else BASE
    hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else END
    window = []
    n = 0
    for ins in sweep(lo, hi):
        window.append(ins)
        if len(window) > 4:
            window.pop(0)
        if len(window) < 3:
            continue
        a, b, c = window[-3], window[-2], window[-1]
        ra = is_mov_load(a, 4)
        if not ra:
            continue
        r1, m1 = ra
        rb = is_mov_load(b)
        if not rb or rb[1].base != r1:
            continue
        r2, m2 = rb
        rc = is_mov_load(c)
        if not rc or rc[1].base != r2:
            continue
        n += 1
        print("---- 0x%08X walk: base=%s : mov %s,[%s+4] ; mov %s,[%s] ; mov %s,[%s]"
              % (a.address, a.reg_name(m1.base), a.reg_name(r1), a.reg_name(m1.base),
                 b.reg_name(r2), a.reg_name(r1), c.reg_name(rc[0]), b.reg_name(r2)))
    print("total:", n)


if __name__ == "__main__":
    main()
