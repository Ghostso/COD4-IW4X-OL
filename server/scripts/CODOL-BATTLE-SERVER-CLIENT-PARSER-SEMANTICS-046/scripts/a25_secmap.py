# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
print("=== section table (image_best.bin) ===")
for s in C.SECS: print("  %-8s VA 0x%08X VSize 0x%08X Raw 0x%08X RSize 0x%08X"%(s["name"],s["va"],s["vsize"],s["raw"],s["rsize"]))
def sec(rva):
    s=C.sec_of(rva); return s["name"] if s else "?"
for r in (0x731E1,0x73214,0x54B7B,0xF26C7,0x1C17B5,0x376B14,0x778D7):
    print("  RVA 0x%06X in section %s"%(r,sec(r)))
print()
print("=== raw bytes around 0x731C0..0x73260 ===")
b=C.raw(0x731C0,0xA0)
print(" ".join("%02X"%x for x in b))
