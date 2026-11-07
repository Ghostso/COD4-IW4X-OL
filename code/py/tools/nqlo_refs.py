#!/usr/bin/env python3
"""nQloP0oCVWR6RDJS 的引用与更大上下文; 查 0x9B6B68 前后是不是常量表头结构。
E 镜像 file offset 0x9B6B68 -> VA 0xDB6B68。找指向它的指针。"""
import struct
E=r"E:\codol_re\client_image_20261027.bin"
d=open(E,"rb").read(); N=len(d); BASE=0x400000
str_off=0x9B6B68
str_va=str_off+BASE
print("nQlo str_off=0x%X VA=0x%X"%(str_off,str_va))

# 找指向 str_va 的 u32 指针
pat=struct.pack("<I",str_va)
i=0;hits=[]
while True:
    p=d.find(pat,i)
    if p<0: break
    hits.append(p); i=p+1
print("指向 nQlo 的指针 (file):",["0x%X(VA0x%X)"%(h,h+BASE) for h in hits[:20]])

# dump 每个指针周围
def show(lo,hi,label):
    lo=max(0,lo);hi=min(N,hi)
    print("=== %s 0x%X-0x%X ==="%(label,lo,hi))
    for i in range(lo,hi,16):
        c=d[i:i+16]
        print("  0x%08X  %-47s  %s"%(i," ".join("%02x"%b for b in c),
              "".join(chr(b) if 32<=b<127 else "." for b in c)))
    print()
for h in hits[:4]:
    show(h-32,h+48,"ptr@0x%X"%h)

# 更大范围看 nQlo 附近是否像结构体表 (前后 256 字节)
show(0x9B6B00,0x9B6C00,"nQlo wide")
