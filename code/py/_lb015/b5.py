# -*- coding: utf-8 -*-
import sys, struct
import fast, img, mem
from img import dword as IDW, read as IRD, call_rel32_hits
M = mem.M
def hx(x): return "0x%X" % x

print("== image callers of 0x724EB0 ==")
print([hx(x) for x in call_rel32_hits(0x724EB0)])
print("== dump callers of 0x724EB0 ==")
print([hx(x) for x in fast.dump_callers(0x724EB0)])

print()
print("== image dword-refs to 0x82E13FC ==")
r = img.dword_refs(0x82E13FC)
print(len(r), [hx(x) for x in r[:80]])
print()
print("== image dword-refs to 0x82E1400 ==")
r2 = img.dword_refs(0x82E1400)
print(len(r2), [hx(x) for x in r2[:40]])
