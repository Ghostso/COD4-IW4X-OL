#!/usr/bin/env python3
"""厘清 u16@[5:7]=(len-10)*4 的真实含义:
   假设A: 头部=8字节 [02][var][u16 0][u16 bitlen], body=x[8:], 那 bitlen vs body?
   假设B: 头部=10字节, body=x[10:], 值=body*4
   检查 u32@[4:8] 各种读法, 以及 'body 是否 dwRoomMessage 位流(首5位=00011)'
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
v2=[x for x in inner if x and x[0]==0x02 and x[1]==0x02]

print("检查 u32@[4:8] LE == (len-10)<<10 ?")
ok=sum(1 for x in v2 if struct.unpack_from("<I",x,4)[0]==((len(x)-10)<<10))
print("  %d/%d"%(ok,len(v2)))
print("检查 u32@[4:8] LE == (len-10)*4 ?")
ok=sum(1 for x in v2 if struct.unpack_from("<I",x,4)[0]==(len(x)-10)*4)
print("  %d/%d"%(ok,len(v2)))

# 若 u32@[4:8]=(len-10)<<10, 说明 = bytes*1024. bytes=len-10. 但 body 若从8开始, len-8.
# 试: u32@[4:8] 是否 == (len-8)<<10 ? (若body从8起)
print("检查 u32@[4:8] == (len-8)<<10 ?")
ok=sum(1 for x in v2 if struct.unpack_from("<I",x,4)[0]==((len(x)-8)<<10))
print("  %d/%d"%(ok,len(v2)))

# body 从10起 是否 dwRoomMessage 位流 (首5位 00011)?
class BR:
    def __init__(s,b): s.b=b;s.pos=0;s.n=len(b)*8
    def bits(s,k):
        v=0
        for _ in range(k):
            if s.pos>=s.n: raise EOFError
            v=(v<<1)|((s.b[s.pos>>3]>>(7-(s.pos&7)))&1);s.pos+=1
        return v
print("\nbody(=x[10:]) 首5位 分布(看是否=3=0x03 消息tag):")
c=collections.Counter()
for x in v2:
    b=x[10:]
    if len(b)>=1:
        br=BR(b);
        try: c[br.bits(5)]+=1
        except EOFError: pass
print("  ",dict(c.most_common(8)))

# 打印前几字节的 bit 视图
print("\n样本 header 逐字节 + body 首字节:")
for x in sorted(set(v2),key=len)[:6]:
    print("  len=%3d hdr=%s body0=%s"%(len(x),x[:10].hex(),x[10:14].hex()))
