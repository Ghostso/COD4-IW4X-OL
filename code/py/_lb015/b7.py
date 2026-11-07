# -*- coding: utf-8 -*-
import sys, struct
import fast, img, mem
from img import dword as IDW, read as IRD, call_rel32_hits
M = mem.M
def hx(x): return "0x%X" % x

print("== callers of 0x632680 (image) ==", [hx(x) for x in call_rel32_hits(0x632680)])
print("== callers of 0x632680 (dump) ==", [hx(x) for x in fast.dump_callers(0x632680)])

for c in (0x63B097,0x63B4E7,0x6C0E43,0x6C2E66,0x724E44,0x736CD5,0x7C509B,0x7C5154,0x7CBCF6,0x7E99DA):
    print("===== insert caller 0x%X =====" % c)
    for insn in img.dis(c-0x40, n=0x40+12):
        if c-0x40 <= insn.address <= c+3:
            print("  %08X %-20s %s" % (insn.address, insn.bytes.hex(), insn.mnemonic+" "+insn.op_str))
    print()

print("== init 0x639D23..0x639D60 ==")
for insn in img.dis(0x639D23, n=0x40):
    print("  %08X %-20s %s" % (insn.address, insn.bytes.hex(), insn.mnemonic+" "+insn.op_str))
    if insn.address >= 0x639D60: break

def rtti_name(vt):
    col = IDW(vt-4)
    td = IDW(col+0x0C)
    nm = IRD(td+8, 64)
    z = nm.find(b"\x00")
    return (hx(col), hx(td), nm[:z].decode("latin1","replace"))

for vt in (0xDC7274,0xDC7714,0xDC73DC,0xDC7474,0xDC787C,0xDC7D4C,0xDC7DBC,0xDC74E0,0xDC7E6C,0xDC74F8,0xDC751C,0xDC7528):
    try:
        print("RTTI vt %s -> %s" % (hx(vt), rtti_name(vt)))
    except Exception as e:
        print("RTTI vt %s ERR %s" % (hx(vt), e))
