# -*- coding: utf-8 -*-
import struct
import img
from img import dword as IDW, read as IRD
def hx(x): return "0x%X" % x
def hd(va, n):
    b = IRD(va, n)
    for off in range(0, len(b), 16):
        row = b[off:off+16]
        print("  %08X  %s  |%s|" % (va+off, " ".join("%02X"%c for c in row), "".join(chr(c) if 32<=c<127 else "." for c in row)))
print("=== 0xD90AD0..0xD90BC0 (WSAStartup area) ===")
hd(0xD90AD0, 0xF0)
print()
print("=== 0xDBC130..0xDCF200 (BATTLE strings) ===")
hd(0xDCF120, 0xA0)
print()
print("=== refs to BATTLE string 0xDCF143 ==", [hx(x) for x in img.dword_refs(0xDCF143)])
print("=== refs to 0xDCF140 ==", [hx(x) for x in img.dword_refs(0xDCF140)])
print("=== refs to Battle string 0xDB7940 ===", [hx(x) for x in img.dword_refs(0xDB7940)])
print("=== refs to 0xDB7944 ===", [hx(x) for x in img.dword_refs(0xDB7944)])
print("=== refs to 0xD90B14 (WSAStartup) ===", [hx(x) for x in img.dword_refs(0xD90B14)])
print("=== refs to 0xD90B10 ===", [hx(x) for x in img.dword_refs(0xD90B10)])
