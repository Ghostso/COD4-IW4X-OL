# -*- coding: utf-8 -*-
"""015: resync-capable linear disassembly of image_best.bin.

Usage:
  python _015_sweep.py <lo_hex> <hi_hex> <disp_hex> [--writes] [--ctx N]
"""
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_MEM, X86_OP_REG  # noqa

WRITE_MNEM = {"mov", "or", "and", "xor", "add", "sub", "xchg", "movzx", "movsx",
              "inc", "dec", "shl", "shr", "sar", "not", "neg"}


def sweep(lo, hi):
    """Yield (ins, prev_list) with resync on decode failure."""
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
        buf = (buf + [ins])[-4:]
        pos += ins.size


def main():
    lo = int(sys.argv[1], 16)
    hi = int(sys.argv[2], 16)
    disp = int(sys.argv[3], 16)
    writes_only = "--writes" in sys.argv
    nctx = 3
    if "--ctx" in sys.argv:
        nctx = int(sys.argv[sys.argv.index("--ctx") + 1])
    total = 0
    hits = 0
    for ins, buf in sweep(lo, hi):
        total += 1
        if not ins.operands or ins.operands[0].type != X86_OP_MEM:
            continue
        m = ins.operands[0].mem
        if m.disp != disp or m.index != 0 or m.base == 0:
            continue
        w = ins.mnemonic in WRITE_MNEM and "dword" in ins.op_str
        if writes_only and not w:
            continue
        if not writes_only and not w and ins.mnemonic not in ("mov", "lea", "cmp"):
            continue
        hits += 1
        print("---- [%s] 0x%08X  %s %s" % ("W" if w else "R", ins.address,
                                          ins.mnemonic, ins.op_str))
        for b in buf[-nctx:]:
            print("       0x%08X  %-20s %s %s" % (b.address, b.bytes.hex(),
                                                  b.mnemonic, b.op_str))
    print("swept %d instructions, %d hits" % (total, hits))


if __name__ == "__main__":
    main()
