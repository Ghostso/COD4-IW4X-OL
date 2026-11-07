#!/usr/bin/env python3
"""精确复核 V=0x02 长度律: u16@[5:7] 到底等于什么?
   候选: (len-10)*4 ? len-10 ? (len-10)*8 ? (len-8)*4 ?
   并打印 header 边界确认 (body 从第几字节开始)。
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

cands={
 "(len-10)*4": lambda L:(L-10)*4,
 "(len-10)*8": lambda L:(L-10)*8,
 "(len-10)":   lambda L:(L-10),
 "(len-8)*4":  lambda L:(L-8)*4,
 "(len-9)*4":  lambda L:(L-9)*4,
 "(len-10)/?": None,
}
print("V=0x02 样本 %d 条, 各候选命中率:"%len(v2))
for name,fn in cands.items():
    if fn is None: continue
    ok=sum(1 for x in v2 if struct.unpack_from("<H",x,5)[0]==fn(len(x)))
    print("  u16 == %-10s : %d/%d"%(name,ok,len(v2)))

print("\n全部 distinct (len, u16@5, 其它候选):")
seen=set()
for x in sorted(v2,key=len):
    L=len(x); u16=struct.unpack_from("<H",x,5)[0]
    if (L,u16) in seen: continue
    seen.add((L,u16))
    print("  len=%3d u16=%4d  (len-10)=%3d  u16/(len-10)=%.2f  header=%s body=%s"%(
        L,u16,L-10,u16/(L-10) if L!=10 else 0, x[:10].hex(), x[10:].hex()[:40]))

# 特别看 len=12 的完整 header
print("\nlen=12 完整 inner:", v2[0].hex() if v2 else None)
for x in v2:
    if len(x)==12:
        print("  len12:",x.hex())
        print("   header[0:10]=%s  body[10:]=%s"%(x[:10].hex(),x[10:].hex()))
        break
