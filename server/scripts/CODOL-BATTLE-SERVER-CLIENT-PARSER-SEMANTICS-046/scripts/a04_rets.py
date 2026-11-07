# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C

lo,hi=0x85D5A0,0x85DB00
print("=== ret / ret-imm sites in 0x%X..0x%X ==="%(lo,hi))
for i in range(lo,hi):
    if C._img[i]==0xC3: print("  ret  @0x%08X"%i)
    if C._img[i]==0xC2: print("  retN @0x%08X imm=%d"%(i, struct.unpack_from("<H",C._img,i+1)[0]))
print()
print("=== prologues (sub esp,imm / push ebp;mov ebp,esp) ===")
for i in range(lo,hi-6):
    if C._img[i]==0x81 and C._img[i+1]==0xEC: print("  sub esp,0x%X @0x%08X"%(struct.unpack_from("<I",C._img,i+2)[0], i))
    if C._img[i]==0x83 and C._img[i+1]==0xEC: print("  sub esp,0x%X @0x%08X"%(C._img[i+2], i))
    if C._img[i]==0x55 and C._img[i+1]==0x8B and C._img[i+2]==0xEC: print("  push ebp;mov ebp,esp @0x%08X"%i)
