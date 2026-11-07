# -*- coding: utf-8 -*-
"""015 probe: confirm image layout, string locations, and global addresses."""
import struct
import sys

from capstone import CS_ARCH_X86, CS_MODE_32, Cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

IMG = (r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline"
       r"\_dyn100_run_20260925_182324\live\image_best.bin")
BASE = 0x400000

data = open(IMG, "rb").read()
print("size = %d (0x%X)" % (len(data), len(data)))
print("VA range = 0x%08X .. 0x%08X" % (BASE, BASE + len(data)))

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def dis(start, end):
    off = start - BASE
    code = data[off:off + (end - start)]
    return list(md.disasm(code, start))


def find_refs(value):
    pat = struct.pack("<I", value)
    out = []
    i = data.find(pat)
    while i >= 0:
        out.append(BASE + i)
        i = data.find(pat, i + 1)
    return out


for label, va in [("mmbook", 0xDC6724), ("mmbook accepted", 0xDC69B0),
                  ("mmbook timedout", 0xDC69D4), ("mmrsv", 0xDE076C)]:
    off = va - BASE
    s = data[off:off + 32].split(b"\x00")[0]
    print("%-18s @0x%08X = %r" % (label, va, s))

print()
print("refs to global 0x82e13fc :", [hex(x) for x in find_refs(0x82E13FC)])
print("refs to global 0x849b61c :", [hex(x) for x in find_refs(0x849B61C)])
print("refs to global 0x849B61C :", [hex(x) for x in find_refs(0x849B61C)])
print()
print("=== 0x7F1520..0x7F1580 ===")
for ins in dis(0x7F1520, 0x7F1580):
    print("0x%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
