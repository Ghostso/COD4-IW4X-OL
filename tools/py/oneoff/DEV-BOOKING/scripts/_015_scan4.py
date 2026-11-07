# -*- coding: utf-8 -*-
"""015: find registration into matching_object+4 (listener list head)."""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD, cstr, dis, show  # noqa
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG  # noqa


def scan_disp_in(disp, start, end, base_reg=None):
    pat = struct.pack("<I", disp)
    out = []
    pos = start - BASE
    hi = end - BASE
    while True:
        i = DATA.find(pat, pos, hi)
        if i < 0:
            break
        pos = i + 1
        va = BASE + i
        best = None
        for back in range(2, 17):
            st = va - back
            if st < BASE:
                continue
            code = DATA[st - BASE: st - BASE + 24]
            ins = next(MD.disasm(code, st), None)
            if ins and ins.address <= va < ins.address + ins.size:
                best = ins
                break
        if best is None:
            continue
        memops = [op for op in best.operands if op.type == X86_OP_MEM]
        if not memops:
            continue
        m = memops[0].mem
        if m.disp != disp or m.index != 0 or m.base == 0:
            continue
        regname = best.reg_name(m.base)
        if base_reg and regname != base_reg:
            continue
        out.append((best, regname))
    return out


WRITE_MNEM = {"mov", "movzx", "movsx", "or", "and", "xor", "add", "sub",
              "inc", "dec", "xchg", "movups", "movaps"}


def main():
    start = int(sys.argv[1], 16)
    end = int(sys.argv[2], 16)
    disp = int(sys.argv[3], 16)
    rows = scan_disp_in(disp, start, end)
    print("range 0x%08X..0x%08X disp=0x%X : %d hits" % (start, end, disp, len(rows)))
    for ins, reg in rows:
        w = ins.operands and ins.operands[0].type == X86_OP_MEM and ins.mnemonic in WRITE_MNEM
        print("  [%s] 0x%08X  %-24s %s %s" % ("W" if w else "R", ins.address,
                                             ins.bytes.hex(), ins.mnemonic, ins.op_str))


if __name__ == "__main__":
    main()
