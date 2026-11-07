# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C

lo,hi=0x85C000,0x85EE00
print("=== 'mov ebp,esp' (8B EC) sites ===")
for i in range(lo,hi-2):
    if C._img[i]==0x8B and C._img[i+1]==0xEC:
        print("  0x%08X  (nearest pad before: 0x%X)"%(i, C._img.rfind(b"\xCC\xCC\xCC",lo,i)+2 if C._img.rfind(b"\xCC\xCC\xCC",lo,i)>=0 else -1))
print()
print("=== 'push ebp; mov ebp,esp' (55 8B EC) sites ===")
for i in range(lo,hi-3):
    if C._img[i]==0x55 and C._img[i+1]==0x8B and C._img[i+2]==0xEC:
        print("  0x%08X"%i)
