# -*- coding: utf-8 -*-
"""015: for each ref to the matching singleton, show the next few instructions
to find listener-list container pointers and broadcast loops."""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa

SINGLETON = 0x82E13FC


def containing(va):
    for back in range(1, 12):
        st = va - back
        code = DATA[st - BASE: st - BASE + 24]
        ins = next(MD.disasm(code, st), None)
        if ins and ins.address <= va < ins.address + ins.size:
            return ins
    return None


def main():
    pat = struct.pack("<I", SINGLETON)
    i = DATA.find(pat)
    while i >= 0:
        va = BASE + i
        ins0 = containing(va)
        if ins0 is not None:
            code = DATA[ins0.address - BASE: ins0.address - BASE + 0x60]
            insns = list(MD.disasm(code, ins0.address))[:8]
            txt = ["%s %s" % (x.mnemonic, x.op_str) for x in insns]
            joined = " | ".join(txt)
            if ("add esi, 4" in joined or "add eax, 4" in joined or
                    "add ebx, 4" in joined or "add ecx, 4" in joined or
                    "add edx, 4" in joined or "add edi, 4" in joined or
                    ", 0x10" in joined):
                print("0x%08X: %s" % (ins0.address, joined))
        i = DATA.find(pat, i + 1)


if __name__ == "__main__":
    main()
