#!/usr/bin/env python3
"""dvar 数字名表邻域: 完整 dump 0x9B8F00-0x9B8FD0 与 0x9D8C30-0x9D8CB0, 还原数字dvar->语义dvar配对。
再看 2486 紧邻 g_difficulty 说明 2486 与难度相关。
"""
import struct
E=r"E:\codol_re\client_image_20261027.bin"
d=open(E,"rb").read(); N=len(d)
def show(lo,hi,label):
    print("=== %s 0x%X-0x%X ==="%(label,lo,hi))
    for i in range(lo,hi,16):
        c=d[i:i+16]
        print("  0x%08X  %-47s  %s"%(i," ".join("%02x"%b for b in c),
              "".join(chr(b) if 32<=b<127 else "." for b in c)))
    print()
show(0x9B8EF0,0x9B8FD0,"dvar names near 2486/2810 (g_difficulty/g_hardcore)")
show(0x9D8C20,0x9D8CC0,"dvar names near 2574 (sv_onboardBonus)")
show(0x9B59C0,0x9B5A20,"dvar names near 3265 (EXE_GAMEISENDING)")

# 解析该区所有 null-terminated 串
def strs(lo,hi):
    out=[];i=lo
    while i<hi:
        e=d.find(b"\x00",i)
        if e<0 or e>hi: break
        s=d[i:e]
        if s and all(32<=b<127 for b in s): out.append(s.decode())
        i=e+1
    return out
print("=== 0x9B8EF0-0x9B8FD0 串 ===")
print(strs(0x9B8EF0,0x9B8FD0))
print("=== 0x9D8C20-0x9D8CC0 串 ===")
print(strs(0x9D8C20,0x9D8CC0))
