# -*- coding: utf-8 -*-
"""015: classify every reference to a global VA in image_best.bin."""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_MEM  # noqa

WRITE_MNEM = {"mov", "or", "and", "xor", "add", "sub", "inc", "dec",
              "movzx", "movsx", "xchg"}


def classify(va_disp):
    for back in range(1, 12):
        st = va_disp - back
        if st < BASE:
            continue
        code = DATA[st - BASE: st - BASE + 24]
        ins = next(MD.disasm(code, st), None)
        if ins and ins.address <= va_disp < ins.address + ins.size:
            return ins
    return None


def main():
    for a in sys.argv[1:]:
        v = int(a, 16)
        pat = struct.pack("<I", v)
        print("=" * 70)
        print("global 0x%08X" % v)
        i = DATA.find(pat)
        n = 0
        while i >= 0:
            va = BASE + i
            ins = classify(va)
            if ins:
                ops = ins.operands
                w = False
                if ops and ops[0].type == X86_OP_MEM and ins.mnemonic in WRITE_MNEM:
                    w = True
                tag = "W" if w else "R"
                print("  %s 0x%08X  %-22s %s %s"
                      % (tag, ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
                n += 1
            i = DATA.find(pat, i + 1)
        print("  total %d" % n)


if __name__ == "__main__":
    main()
