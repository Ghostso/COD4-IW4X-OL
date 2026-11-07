#!/usr/bin/env python3
"""检查 0xA4E8xx 表前后更广范围, 找可能的 {u32 serviceId, char* name} 结构;
以及 E 镜像里所有紧邻 0x66 的服务名指针 (id=102 的服务注册)。"""
import struct
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()
N = len(data); BASE = 0x400000

def show(lo,hi,label):
    print("=== %s file0x%X-0x%X ==="%(label,lo,hi))
    for i in range(lo,hi,16):
        c=data[i:i+16]
        print("  0x%08X  %-47s  %s"%(i," ".join("%02x"%b for b in c),
              "".join(chr(b) if 32<=b<127 else "." for b in c)))
    print()

show(0xA4E7C0,0xA4E8C0,"before table")

def read_cstr(va):
    off=va-BASE
    if off<0 or off>=N: return None
    end=data.find(b"\x00",off)
    if end<0 or end-off>40: return None
    s=data[off:end]
    if all(32<=b<127 for b in s) and s: return s.decode("latin1")
    return None

print("=== 全镜像: u32==102 且下一 u32 是指向服务名 C串的指针 ===")
i=0; hits=[]
while i+8<=N:
    if data[i]==0x66 and data[i+1]==0 and data[i+2]==0 and data[i+3]==0:
        ptr=struct.unpack_from("<I",data,i+4)[0]
        nm=read_cstr(ptr)
        if nm: hits.append((i,ptr,nm))
    i+=4
print("命中:",len(hits))
for off,ptr,nm in hits[:60]:
    print("  file0x%08X VA0x%08X  id=102 -> %r (ptrVA0x%X)"%(off,off+BASE,nm,ptr))

print("\n=== 反查: 服务名 ptr 前面 4 字节是 102 的 ===")
for name in ["messaging","marketplace","matchmaking","storage","profiles","eventlog","titleutilities","tencent","teams","friends","mail","pooledstorage","stats","reward","tags","group"]:
    nb=name.encode()+b"\x00"
    j=0
    while True:
        p=data.find(nb,j)
        if p<0: break
        j=p+1
        va=p+BASE
        # 搜所有指向 va 的 u32
        pat=struct.pack("<I",va)
        k=0
        while True:
            q=data.find(pat,k)
            if q<0: break
            k=q+1
            if q>=4:
                pre=struct.unpack_from("<I",data,q-4)[0]
                if pre==102:
                    print("  %s: ptr@file0x%X, 前置u32=102"%(name,q))
