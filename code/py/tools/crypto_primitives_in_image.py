#!/usr/bin/env python3
"""§七 #3 帧头/加密/HMAC 层: 在 E 运行时镜像里独立验证密码学原语是否真在客户端。
   (1) AES-128 S-box 表 (FIPS-197 标准 256B)
   (2) AES 逆 S-box
   (3) SHA-1 轮常量 0x5A827999/0x6ED9EBA1/0x8F1BBCDC/0xCA62C1D6
   (4) 密钥派生标签 'CLIENTCHAL' / 'BDDATA'
   (5) 帧标记 0xAB/0x85 的成对出现
"""
import struct, os
E=r"E:\codol_re\client_image_20261027.bin"

# FIPS-197 标准 S-box
SBOX=bytes.fromhex(
"637c777bf26b6fc53001672bfed7ab76"
"ca82c97dfa5947f0add4a2af9ca472c0"
"b7fd9326363ff7cc34a5e5f171d83115"
"04c723c31896059a071280e2eb27b275"
"09832c1a1b6e5aa0523bd6b329e32f84"
"53d100ed20fcb15b6acbbe394a4c58cf"
"d0efaafb434d338545f9027f503c9fa8"
"51a3408f929d38f5bcb6da2110fff3d2"
"cd0c13ec5f974417c4a77e3d645d1973"
"60814fdc222a908846eeb814de5e0bdb"
"e0323a0a4906245cc2d3ac629195e479"
"e7c8376d8dd54ea96c56f4ea657aae08"
"ba78252e1ca6b4c6e8dd741f4bbd8b8a"
"703eb5664803f60e613557b986c11d9e"
"e1f8981169d98e949b1e87e9ce5528df"
"8ca1890dbfe6426841992d0fb054bb16")

# SHA-1 常量
SHA1_K=[0x5A827999,0x6ED9EBA1,0x8F1BBCDC,0xCA62C1D6]

def find_all(d,pat,limit=8):
    hits=[];i=0
    while True:
        p=d.find(pat,i)
        if p<0: break
        hits.append(p);i=p+1
        if len(hits)>=limit: break
    return hits

print("=== (1) AES S-box 表 ===")
print("  长度=%d 字节"%len(SBOX))
h=find_all(E if False else b"",b"")  # placeholder
try:
    d=open(E,"rb").read()
except Exception as ex:
    print("  E 读失败:",ex); raise SystemExit
hits=find_all(d,SBOX)
print("  E 镜像命中 %d 处: %s"%(len(hits),["0x%X"%x for x in hits]))

# 逆 S-box
INV=bytearray(256)
for i,v in enumerate(SBOX): INV[v]=i
hits_i=find_all(d,bytes(INV))
print("  逆 S-box 命中 %d 处: %s"%(len(hits_i),["0x%X"%x for x in hits_i]))

print("\n=== (2) SHA-1 轮常量 (LE 和 BE) ===")
for K in SHA1_K:
    le=struct.pack("<I",K); be=struct.pack(">I",K)
    hl=find_all(d,le,4); hb=find_all(d,be,4)
    print("  K=0x%08X  LE命中=%s  BE命中=%s"%(K,["0x%X"%x for x in hl],["0x%X"%x for x in hb]))

print("\n=== (3) 密钥派生标签 ===")
for lab in [b"CLIENTCHAL",b"BDDATA",b"CLIENTCHAL\x00",b"BDDATA\x00"]:
    hits=find_all(d,lab,4)
    print("  %-14r 命中 %d: %s"%(lab,len(hits),["0x%X"%x for x in hits]))

print("\n=== (4) 帧标记 AB 85 / 85 AB ===")
for pat in [b"\xab\x85",b"\x85\xab"]:
    hits=find_all(d,pat,6)
    print("  %s 命中 %d: %s"%(pat.hex(),len(hits),["0x%X"%x for x in hits]))

print("\n=== (5) HMAC-SHA1 的 ipad/opad 0x36/0x5c 重复块 ===")
# HMAC 的 64 字节 ipad(0x36)/opad(0x5c) 通常不会以常量出现, 但看是否有 64*0x36
print("  64×0x36 命中:",len(find_all(d,bytes([0x36])*64,3)))
print("  64×0x5c 命中:",len(find_all(d,bytes([0x5c])*64,3)))
