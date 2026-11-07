#!/usr/bin/env python3
"""分析 0x722EC00 处的 0..129 置换表: 是否覆盖 0..129? 102 位置? 上下文用途?"""
import struct
E=r"E:\codol_re\client_image_20261027.bin"
data=open(E,"rb").read()
off=0x0722EC00
vals=[struct.unpack_from("<I",data,off+k)[0] for k in range(0,130*4,4)]
print("长度:",len(vals))
print("min=%d max=%d unique=%d"%(min(vals),max(vals),len(set(vals))))
print("是否 0..129 全排列:", sorted(vals)==list(range(130)))
print("vals[102] =", vals[102], " 位置 of 102:", vals.index(102) if 102 in vals else None)
# 打印表头前 24 项与 102 邻域
print("vals[96:112] =", vals[96:112])
# 查表前后是什么
print("\n=== 表前 0x722EB80-0x722EC00 ===")
for i in range(0x722EB80,0x722EC00,16):
    c=data[i:i+16]
    print("  0x%08X  %-47s  %s"%(i," ".join("%02x"%b for b in c),
          "".join(chr(b) if 32<=b<127 else "." for b in c)))
print("\n=== 表后 0x722EE00-0x722EF00 ===")
for i in range(0x722EE00,0x722EF00,16):
    c=data[i:i+16]
    print("  0x%08X  %-47s  %s"%(i," ".join("%02x"%b for b in c),
          "".join(chr(b) if 32<=b<127 else "." for b in c)))
