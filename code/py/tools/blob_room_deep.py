#!/usr/bin/env python3
"""0x02族(room data) 深解:
   (a) byte[4:8] 是不是 bit长度/字节长度? 与实际长度关系
   (b) LSB-first 位流解码试探
   (c) 'ab ab' 高频段是否可作 float32/固定结构
   (d) 取一条长样本完整 u32 dump + float dump
"""
import json, struct, collections
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())
FIXED={0x01:1,0x03:1,0x06:2,0x07:4,0x08:4,0x09:8,0x0a:8}
def blobs(payload):
    out=[];i=0;n=len(payload)
    while i<n:
        t=payload[i];i+=1
        if t==0x00: continue
        if t==0x10:
            j=payload.find(b"\x00",i)
            if j<0: break
            i=j+1;continue
        if t in FIXED: i+=FIXED[t];continue
        if t in (0x13,0x6b,0x6c):
            if i>=n or payload[i]!=0x08: break
            i+=1
            if i+4>n:break
            ln=struct.unpack_from("<I",payload,i)[0];i+=4
            data=payload[i:i+ln];i+=ln
            if t in(0x6b,0x6c): i+=4
            if t==0x13: out.append(data)
            continue
        break
    return out
inner=[]
for r in recs:
    if r.get("svc")==11 and r.get("task")==4:
        for d in blobs(bytes.fromhex(r["payload"])):
            if len(d)>=4 and struct.unpack_from("<I",d,0)[0]==len(d)-4:
                inner.append(d[4:])
fam02=[x for x in inner if x and x[0]==0x02]

print("### (a) byte[4:8] vs 长度")
print(" len  b1  b4  b5  b6  b7   u32LE[4:8]  (len-8)*8  (len-4)*8  b5*8")
seen=set()
for x in sorted(fam02,key=len):
    key=(len(x),x[1])
    if key in seen: continue
    seen.add(key)
    b4,b5,b6,b7=x[4],x[5],x[6],x[7]
    u=struct.unpack_from("<I",x,4)[0]
    print("  %3d %02x  %02x  %02x  %02x  %02x   %-10d  %-8d  %-8d  %d"%(
        len(x),x[1],b4,b5,b6,b7,u,(len(x)-8)*8,(len(x)-4)*8,b5*8))

print("\n### (b) LSB-first 位流 试探 (offset 0..24)")
class BRlsb:
    def __init__(s,b,o=0): s.b=b;s.pos=o;s.n=len(b)*8
    def bits(s,k):
        v=0
        for i in range(k):
            if s.pos>=s.n: raise EOFError
            byte=s.b[s.pos>>3]; bit=(byte>>(s.pos&7))&1  # LSB first
            v|=bit<<i; s.pos+=1
        return v
WIDTH={0x01:1,0x02:8,0x03:8,0x05:16,0x06:16,0x07:32,0x08:32,0x0a:64,0x0d:32}
def dec_lsb(b,off):
    br=BRlsb(b,off)
    try:
        while br.n-br.pos>=5:
            tag=br.bits(5)
            if tag in WIDTH: br.bits(WIDTH[tag])
            elif tag==0x15: return False
            elif tag==0x10:
                while br.bits(8)!=0: pass
            elif tag==0x13:
                if br.bits(5)!=0x08: return False
                br.bits(br.bits(32)*8)
            else: return False
        return True
    except EOFError: return False
for off in range(0,25):
    c=sum(1 for x in fam02 if dec_lsb(x,off))
    if c: print("  LSB offset=%2d clean=%d"%(off,c))
print("  (无输出=LSB也不成立)")

print("\n### (d) 长样本 u32+float dump: len141 最常见形态")
for x in fam02:
    if len(x)==141:
        print("  hex:",x.hex())
        print("  u32:")
        for i in range(0,len(x)-3,4):
            u=struct.unpack_from("<I",x,i)[0]
            f=struct.unpack_from("<f",x,i)[0]
            print("    [%3d] 0x%08X  %-12d  f=%g"%(i,u,u,f))
        break
