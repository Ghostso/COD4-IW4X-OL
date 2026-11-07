# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
def nearfunc(addr):
    lo=addr-0x600
    # find candidate starts by scanning back for int3 runs or common prologues
    for i in range(addr, lo, -1):
        if C._img[i-1]==0xCC and C._img[i]!=0xCC: return i
    return None
for a in (0x66F410,0x671FF9,0x673267,0x422A90,0x464913):
    fs=nearfunc(a); print("site 0x%X -> func start ~0x%X"%(a, fs))
print()
print(C.dump(0x66F410,0x66F520,"0x66F410 (native mixed reader)"))
