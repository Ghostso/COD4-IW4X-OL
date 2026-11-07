#!/usr/bin/env python3
"""room族(0x02) 最终: 全字节offset扫位流, 要求首字段=tag0x03且type 0..46;
   并验证 header 字段: u16@[5:7] 对 variant02 是否 ==(len-10)*4; 各variant的[4:8]语义。
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
room=[x for x in inner if x and x[0]==0x02]

class BR:
    def __init__(s,b,o=0): s.b=b;s.pos=o;s.n=len(b)*8
    def bits(s,k):
        v=0
        for _ in range(k):
            if s.pos>=s.n: raise EOFError
            v=(v<<1)|((s.b[s.pos>>3]>>(7-(s.pos&7)))&1); s.pos+=1
        return v
WIDTH={0x01:1,0x02:8,0x03:8,0x05:16,0x06:16,0x07:32,0x08:32,0x0a:64,0x0d:32}
def dec(b,off):
    br=BR(b,off)
    try:
        first_tag=br.bits(5)
        if first_tag!=0x03: return None
        typ=br.bits(8)
        if typ>46: return None
        # continue decode
        n=1
        while br.n-br.pos>=5:
            tag=br.bits(5)
            if tag in WIDTH: br.bits(WIDTH[tag])
            elif tag==0x15: return ("15",typ)
            elif tag==0x10:
                while br.bits(8)!=0: pass
            elif tag==0x13:
                if br.bits(5)!=0x08: return ("badsub",typ)
                br.bits(br.bits(32)*8)
            else: return ("bad%02x"%tag,typ)
            n+=1
        return ("clean%d"%n,typ)
    except EOFError: return ("eof",None)

print("room族 扫 byte offset 0..20, 只统计首字段=tag0x03&type<=46:")
for off in range(0,21):
    hits=collections.Counter()
    for x in room:
        r=dec(x,off*8)
        if r: hits[r[0]]+=1
    if hits:
        print("  byteoff=%2d : %s"%(off,dict(hits.most_common(6))))
print("(若全无 -> room族内层不是dwRoomMessage位流)")

print("\n### header 字段语义: 各variant的 u16@[5:7] 与 len 关系")
for v in [2,4,6,8]:
    xs=[x for x in room if x[1]==v]
    print("variant 0x%02X (%d条):"%(v,len(xs)))
    for x in sorted(set(xs),key=len)[:12]:
        u16=struct.unpack_from("<H",x,5)[0]
        u32=struct.unpack_from("<I",x,4)[0]
        print("   len=%3d  u16@5=%-6d (len-10)*4=%-6d  u32@4=0x%08X  b8=%02x b9=%02x"%(
            len(x),u16,(len(x)-10)*4,u32,x[8],x[9]))
