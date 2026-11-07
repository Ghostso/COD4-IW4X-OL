# -*- coding: utf-8 -*-
"""找出 [reg+0x3A048] / [reg+0x3A04C] 的写入点，判断字段A/B 由谁设置。"""
import struct
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
img = open(IMG, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)


def scan(disp, label):
    pat = struct.pack("<I", disp)
    hits = []
    s = 0
    while True:
        i = img.find(pat, s)
        if i < 0:
            break
        hits.append(i)
        s = i + 1
    print("=" * 70)
    print("disp=0x%X  (%s)  出现 %d 处" % (disp, label, len(hits)))
    print("=" * 70)
    for i in hits:
        va = 0x400000 + i
        start = va - 6
        ins_line = None
        for ins in md.disasm(img[start - 0x400000:start - 0x400000 + 0x14], start):
            if ins.address <= va < ins.address + ins.size:
                ins_line = "%08X  %-12s %s" % (ins.address, ins.mnemonic, ins.op_str)
        print("  %s" % (ins_line or ("0x%08X ?" % va)))
    print()


if __name__ == "__main__":
    scan(0x3A048, "field A")
    scan(0x3A04C, "field B")
