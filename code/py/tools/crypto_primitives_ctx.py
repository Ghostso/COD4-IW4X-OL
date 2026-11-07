#!/usr/bin/env python3
"""补强 §七 #3 独立验证:
   (a) 逆 S-box @0x884C40 上下文 (确认是完整 AES 表, VA=0x884C40+0x400000=0xC84C40)
   (b) 找 AES 前向 S-box 的替代形态 (T-table Te0 首项 0xc66363a5, 或 fwd-sbox XOR 逆)
   (c) SHA-1 4 常量区的距离/是否同段 (判断是一个 SHA-1 实现还是多个)
   (d) CLIENTCHAL/BDDATA 上下文 (是否 8/8 相邻, VA 换算)
"""
import struct
E=r"E:\codol_re\client_image_20261027.bin"
d=open(E,"rb").read(); N=len(d)
BASE=0x400000

def dump(lo,hi,label):
    print("=== %s file0x%X (VA 0x%X) ==="%(label,lo,lo+BASE))
    for i in range(lo,hi,16):
        c=d[i:i+16]
        print("  file0x%08X  %-47s  %s"%(i," ".join("%02x"%b for b in c),
              "".join(chr(b) if 32<=b<127 else "." for b in c)))

# (a) 逆 S-box 上下文
dump(0x884C30,0x884C50,"inv S-box start@0x884C40")
# 逆 S-box 表尾 (inv[255]=0x16? 逆表末项)
INV=bytes.fromhex(
"52096a"+"d538a5"+"30361a2e"+"4a2c0b"
"") # 占位, 用计算
SBOX=bytes.fromhex(
"637c777bf26b6fc53001672bfed7ab76ca82c97dfa5947f0add4a2af9ca472c0"
"b7fd9326363ff7cc34a5e5f171d83115" "04c723c31896059a071280e2eb27b275"
"09832c1a1b6e5aa0523bd6b329e32f84" "53d100ed20fcb15b6acbbe394a4c58cf"
"d0efaafb434d338545f9027f503c9fa8" "51a3408f929d38f5bcb6da2110fff3d2"
"cd0c13ec5f974417c4a77e3d645d1973" "60814fdc222a908846eeb814de5e0bdb"
"e0323a0a4906245cc2d3ac629195e479" "e7c8376d8dd54ea96c56f4ea657aae08"
"ba78252e1ca6b4c6e8dd741f4bbd8b8a" "703eb5664803f60e613557b986c11d9e"
"e1f8981169d98e949b1e87e9ce5528df"
"8ca1890dbfe6426841992d0fb054bb16")
inv=[0]*256
for i,v in enumerate(SBOX): inv[v]=i
inv=bytes(inv)
p=0x884C40
print("  验证: d[0x884C40:0x884C40+256] == 标准逆S-box : %s"%(d[p:p+256]==inv))
print("  逆S-box 后 16 字节:",d[p+256:p+272].hex())

# (b) 前向 S-box 替代形态
print("\n=== (b) 前向 S-box 替代形态搜索 ===")
# Te0 标准首项 0xc66363a5 (LE bytes a5 63 63 c6)
for name,pat in [
  ("Te0首项 LE", struct.pack("<I",0xc66363a5)),
  ("Te0首项 BE", struct.pack(">I",0xc66363a5)),
  ("Td0首项 LE", struct.pack("<I",0x51f4a750)),
  ("fwd S-box 前16B", SBOX[:16]),
]:
    hits=[];i=0
    while True:
        x=d.find(pat,i)
        if x<0: break
        hits.append(x);i=x+1
        if len(hits)>=4: break
    print("  %-16s %s 命中 %d: %s"%(name,pat.hex(),len(hits),["0x%X"%h for h in hits]))

# (c) SHA-1 常量距离
print("\n=== (c) SHA-1 常量区 ===")
K=[0x5A827999,0x6ED9EBA1,0x8F1BBCDC,0xCA62C1D6]
for i,k in enumerate(K):
    hits=[];j=0
    pat=struct.pack("<I",k)
    while True:
        x=d.find(pat,j)
        if x<0: break
        hits.append(x);j=x+1
    print("  K%d=0x%08X 命中%d次, 前6=%s"%(i+1,k,len(hits),["0x%X"%h for h in hits[:6]]))

# (d) KDF 标签上下文
print("\n=== (d) CLIENTCHAL / BDDATA 上下文 ===")
dump(0x95A4D8,0x95A500,"KDF labels")

# 帧标记 AB85 上下文(取一个像代码的)
print("\n=== (e) AB85 命中之一上下文(0x6FA141) ===")
dump(0x6FA130,0x6FA160,"ab85 @0x6FA141")
