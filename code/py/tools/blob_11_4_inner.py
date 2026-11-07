#!/usr/bin/env python3
"""11/4 blob 内层(剥u32长度头)完整解剖: 每类起点('02 0X 00 00' vs '18 1c 5a 98')样本全 hex + 长度关系."""
import json, collections, struct
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
        p=bytes.fromhex(r["payload"])
        for d in blobs(p):
            if len(d)>=4 and struct.unpack_from("<I",d,0)[0]==len(d)-4:
                inner.append(d[4:])

# 按起点分类
by=collections.defaultdict(list)
for x in inner:
    by[x[:4].hex()].append(x)
print("11/4 inner total=%d"%len(inner))
for k,v in sorted(by.items(),key=lambda kv:-len(kv[1])):
    print("\n=== start %s : %d samples, innerlen set=%s ==="%(k,len(v),sorted(set(len(x) for x in v))[:8]))
    for x in v[:3]:
        print("   len=%3d  %s"%(len(x),x.hex()))

# 检查 '02 0X 00 00' 类: 0X 与长度/元素数关系
print("\n\n### 02-class 分析: u16@2 与 innerlen 关系")
c=collections.Counter()
for x in inner:
    if x[:1]==b'\x02':
        u16_2=struct.unpack_from("<H",x,2)[0] if len(x)>=4 else -1
        c[(x[1],u16_2,len(x))]+=1
for k,v in sorted(c.items()):
    print("  type=0x%02x u16@2=%-6d innerlen=%-4d cnt=%d"%k if isinstance(k[0],int) else (k,v))
