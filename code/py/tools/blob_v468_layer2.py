#!/usr/bin/env python3
"""V=0x04/06/08 第二层结构: 逐长度组 dump 完整 hex, 找内部长度字段。
   已知 V=02: u32@[4:8]=(len-10)<<10。V=04/06/08 该字段不是整块长度。
   假设: 头仍是10字节, body 内部有第二层 u32 长度前缀。
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

for V in (4,6,8):
    xs=[x for x in inner if x and x[0]==0x02 and x[1]==V]
    print("="*72)
    print("V=0x%02X : %d 条, %d distinct"%(V,len(xs),len(set(xs))))
    # 逐字节方差 (只看 len==最长组 或 全部)
    bylen=collections.defaultdict(list)
    for x in xs: bylen[len(x)].append(x)
    big=sorted(bylen,key=lambda L:-len(bylen[L]))[:2]
    for L in big:
        grp=bylen[L]
        print("  -- len=%d (%d 样本) 每字节 distinct --"%(L,len(grp)))
        const=[];var=[]
        for i in range(L):
            vals=collections.Counter(x[i] for x in grp)
            if len(vals)==1: const.append((i,vals.most_common(1)[0][0]))
            else: var.append((i,len(vals)))
        print("     恒定字节:",[(i,"%02x"%v) for i,v in const][:20])
        print("     可变字节 idx:",[i for i,_ in var][:30])
    # distinct 完整 hex (按长度)
    print("  distinct 全览:")
    for x in sorted(set(xs),key=lambda t:(len(t),t)):
        u32=struct.unpack_from("<I",x,4)[0]
        u16=struct.unpack_from("<H",x,5)[0]
        print("   len=%3d u32@4=0x%08X u16@5=%-4d body=%s"%(len(x),u32,u16,x[10:].hex()))
