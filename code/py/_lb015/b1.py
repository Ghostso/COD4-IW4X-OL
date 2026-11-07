# -*- coding: utf-8 -*-
import sys, struct
import fast, img, mem
from img import dword as IDW, read as IRD, call_rel32_hits
M = mem.M

def hx(x): return "0x%X" % x

def dump_vt(vt, n=16):
    print("--- vtable %s ---" % hx(vt))
    for i in range(n):
        v = IDW(vt + 4*i)
        tag = ""
        if 0x401000 <= v < 0xE65000:
            b = IRD(v, 4)
            tag = "code " + b.hex()
        print("  +0x%02X = %s  %s" % (4*i, hx(v), tag))

print("== image_best callers 0x638210 ==", [hx(x) for x in call_rel32_hits(0x638210)])
print("== dump callers 0x638210 ==", [hx(x) for x in fast.dump_callers(0x638210)])

for vt in (0xDC7274, 0xDC7714, 0xDC73DC, 0xDC7474, 0xDC7D4C, 0xDC7DBC, 0xDC787C, 0xDC74E0, 0xDC7E6C):
    try:
        dump_vt(vt, 16)
    except Exception as e:
        print("vt %s ERR %s" % (hx(vt), e))

print()
print("== disasm 0x638210 ==")
for ins in img.dis(0x638210, count=120):
    print("  %08X %-22s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic+" "+ins.op_str))
    if ins.address >= 0x6382E5:
        break
