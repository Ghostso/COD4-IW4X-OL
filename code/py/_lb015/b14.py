# -*- coding: utf-8 -*-
import struct
import img
from img import dword as IDW, read as IRD
def hx(x): return "0x%X" % x
print("=== disasm 0xE4A740 area (ws2 loader) ===")
for i in img.dis(0xE4A740, n=0x200):
    print("  %08X %-18s %s" % (i.address, i.bytes.hex(), i.mnemonic+" "+i.op_str))
    if i.address > 0xE4A940: break
print()
for s in (0xD90B50,0xD90B5C,0xD90B6C,0xD90B84,0xDB7940,0xE4A7E4):
    print("refs to",hx(s), [hx(x) for x in img.dword_refs(s)])
