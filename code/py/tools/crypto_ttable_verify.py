#!/usr/bin/env python3
"""§七 #3 最强验证: AES T-table (Te0/Te1/Te2/Te3, Td0..Td3) 完整性 + HMAC/AES 错误串登记表。
   T-table 标准首项已见: Te0 BE@0x883940/44, Td0 LE@0x95BB48/0x95EC90.
   Te0 = 0xc66363a5 起, 256 项; 验证后续项是否匹配标准表。
   标准表(前8项)可硬编码测试。
"""
import struct
E=r"E:\codol_re\client_image_20261027.bin"
d=open(E,"rb").read()
BASE=0x400000

# 标准 AES Te0 (FIPS 197 T-table) 前 8 项
Te0=[0xc66363a5,0xf87c7c84,0xee777799,0xf67b7b8d,0xfff2f20d,0xd66b6bbd,0xde6f6fb1,0x91c5c554]
Td0=[0x51f4a750,0x7e416553,0x1a17a4c3,0x3a275e96,0x3bab6bcb,0x1f9d45f1,0xacfa58ab,0x4be30393]

def check_table(label, base_off, vals, endian):
    print("=== %s @file0x%X (VA 0x%X) %s ==="%(label,base_off,base_off+BASE,endian))
    ok=True
    for i,v in enumerate(vals):
        b=struct.pack(endian+"I",v)
        off=base_off+i*4
        got=d[off:off+4]
        if got!=b:
            print("  项%d 不匹配: 期望 %s 实际 %s (file0x%X)"%(i,b.hex(),got.hex(),off));ok=False
    print("  前%d项逐项匹配: %s"%(len(vals),ok))
    # 校验 256 项区域熵
    region=d[base_off:base_off+256*4]
    print("  256项区域是否全非零:",all(region))
    return ok

# Te0 BE @ 0x883940, LE @ 0x95B348
check_table("Te0",0x883940,Te0,">")
check_table("Te0",0x95B348,Te0,"<")
# Td0 LE @ 0x95BB48 / 0x95EC90
check_table("Td0",0x95BB48,Td0,"<")
check_table("Td0",0x95EC90,Td0,"<")

# 找 Te1(循环移位 8) / Te2(16) / Te3(24)
def rot(v,s):
    return ((v<<s)|(v>>(32-s)))&0xFFFFFFFF
print("\n=== Te1/Te2/Te3 (Te0 循环移位) 搜索 ===")
for s,name in [(8,"Te1"),(16,"Te2"),(24,"Te3")]:
    pat=struct.pack(">I",rot(Te0[0],s))
    hits=[];i=0
    while True:
        x=d.find(pat,i)
        if x<0: break
        hits.append(x);i=x+1
        if len(hits)>=3: break
    print("  %s 首项 %s BE 命中: %s"%(name,pat.hex(),["0x%X"%h for h in hits]))

# 错误串登记表: 在 KDF 标签之后
print("\n=== 密码学相关错误串 ===")
import re
region=d[0x95A4D8:0x95B400]
for m in re.finditer(rb"[ -~]{6,}",region):
    s=m.group(0)
    print("  file0x%X  %r"%(0x95A4D8+m.start(),s.decode()))
