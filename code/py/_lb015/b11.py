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
print("=== 0xD94480..0xD94640 ===")
hd(0xD94480, 0x1C0)
print()
print("=== disasm 0x5B8570 (127.0.0.1 code) ===")
for i in img.dis(0x5B8570, n=0x50):
    print("  %08X %-16s %s" % (i.address, i.bytes.hex(), i.mnemonic+" "+i.op_str))
print()
print("=== disasm 0x7F5C10 (127.0.0.1 code) ===")
for i in img.dis(0x7F5C10, n=0x60):
    print("  %08X %-16s %s" % (i.address, i.bytes.hex(), i.mnemonic+" "+i.op_str))
print()
print("== refs to 0xD9453A / 0xD94597 (image) ==")
for t in (0xD9453A, 0xD94597, 0xD94538, 0xD94594):
    print(hx(t), [hx(x) for x in img.dword_refs(t)])
