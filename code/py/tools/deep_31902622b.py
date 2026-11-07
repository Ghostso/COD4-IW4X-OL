#!/usr/bin/env python3
"""31902622 再试: FNV1/FNV1a/CRC32变体/Java hashCode/djb2/MAC字节运算/会话串字节运算。"""
import zlib, hashlib
V=31902622
sess=b"nQloP0oCVWR6RDJS"
mac_str=b"D4-93-90-18-55-10"
mac_hex=bytes([0xD4,0x93,0x90,0x18,0x55,0x10])

def fnv1a32(b):
    h=0x811c9dc5
    for c in b: h=((h^c)*0x01000193)&0xffffffff
    return h
def fnv1_32(b):
    h=0x811c9dc5
    for c in b: h=((h*0x01000193)&0xffffffff)^c
    return h
def djb2(b):
    h=5381
    for c in b: h=((h*33)+c)&0xffffffff
    return h
def djb2x(b):
    h=5381
    for c in b: h=((h*33)^c)&0xffffffff
    return h
def java_hash(b):
    h=0
    for c in b: h=((h*31)+c)&0xffffffff
    return h
def sdbm(b):
    h=0
    for c in b: h=(c+(h<<6)+(h<<16)-h)&0xffffffff
    return h

cands={"sess":sess,"mac_str":mac_str,"mac_hex":mac_hex,"sess+mac":sess+mac_str}
funcs={"fnv1a":fnv1a32,"fnv1":fnv1_32,"djb2":djb2,"djb2x":djb2x,"java":java_hash,"sdbm":sdbm,
       "crc32":lambda b: zlib.crc32(b)&0xffffffff,
       "crc32c_naive":None}
print("V=0x%08X"%V)
hit=False
for cn,cb in cands.items():
    for fn,f in funcs.items():
        if f is None: continue
        v=f(cb)
        if v==V:
            print("HIT %s(%s)"%(fn,cn)); hit=True
# adler32
for cn,cb in cands.items():
    if (zlib.adler32(cb)&0xffffffff)==V: print("HIT adler32(%s)"%cn); hit=True
print("hash hits:", hit)

# MAC 字节算术
import struct
vals={"mac_le_u32_first4":struct.unpack("<I",mac_hex[:4])[0],
      "mac_be_u32_first4":struct.unpack(">I",mac_hex[:4])[0],
      "mac_le_last4":struct.unpack("<I",mac_hex[2:6])[0],
      "mac_be_last4":struct.unpack(">I",mac_hex[2:6])[0]}
for k,v in vals.items(): print("  %s = %d (0x%X)"%(k,v,v))

# V 是否 = 某 XOR/sum of MAC bytes 扩展
print("\nMAC bytes:", [hex(x) for x in mac_hex])
print("sum=",sum(mac_hex), "xor=", __import__("functools").reduce(lambda a,b:a^b, mac_hex))

# 是否 31902622 的十进制数字 3-1-9-0-2-6-2-2 有啥
print("\nV digits:", str(V))
print("V hex:", hex(V), "→", [hex(ord(c)) for c in "31902622"])
