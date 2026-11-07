#!/usr/bin/env python3
"""完整反汇编看 0xA6300-0xA6500 附近的 71/4 序列化函数; 找 31902622 来源。"""
import struct
E=r"E:\codol_re\client_image_20261027.bin"
d=open(E,"rb").read(); N=len(d); BASE=0x400000
def show(lo,hi,label):
    lo=max(0,lo);hi=min(N,hi)
    print("=== %s 0x%X-0x%X (VA 0x%X) ==="%(label,lo,hi,lo+BASE))
    for i in range(lo,hi,16):
        c=d[i:i+16]
        print("  0x%08X  %-47s  %s"%(i," ".join("%02x"%b for b in c),
              "".join(chr(b) if 32<=b<127 else "." for b in c)))
    print()
show(0xA6300,0xA6520,"71/4 serializer func")

# 搜 0x2b2b2b2b 立即数其它出现 (确认是同一函数族)
pat=b"\x2b\x2b\x2b\x2b"
i=0;hits=[]
while True:
    p=d.find(pat,i)
    if p<0: break
    hits.append(p); i=p+1
    if len(hits)>=20: break
print("0x2b2b2b2b 出现 (file):",["0x%X"%h for h in hits[:20]], "total", len(hits))

# 找 31902622 是否可能由 nearby 全局持有: dump 全局区 0xDB6B60-0xDB6B90 的实际字节
show(0x9B6B60,0x9B6B90,"globals at DB6B60")
