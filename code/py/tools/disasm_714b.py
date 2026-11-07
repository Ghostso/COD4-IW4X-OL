#!/usr/bin/env python3
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
show(0xA6180,0xA6310,"before serializer")
# 搜 31902622 作为立即数 (已试过 LE/BE 全镜像 0 命中), 试作为 8字节/其它偏移
V=31902622
for fmt in ["<I",">I","<Q",">Q"]:
    try:
        pat=struct.pack(fmt,V)
    except: continue
    i=0;hits=[]
    while True:
        p=d.find(pat,i)
        if p<0: break
        hits.append(p); i=p+1
    print("V fmt %s hits=%d %s"%(fmt,len(hits),["0x%X"%h for h in hits[:5]]))
# 附近 push imm32 里是否有接近 31902622 的
print("\n=== 0xA6180-0xA6310 内的 push imm32 (68 xx xx xx xx) ===")
for i in range(0xA6180,0xA6310):
    if d[i]==0x68 and i+5<=N:
        imm=struct.unpack_from("<I",d,i+1)[0]
        print("  0x%X push 0x%08X (%d)"%(i+BASE,imm,imm))
