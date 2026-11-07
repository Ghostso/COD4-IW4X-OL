#!/usr/bin/env python3
"""11/4 blob 内层 0x02族: 去重全部 distinct 形态, 完整 hex, 按长度排序。找固定模板 + 可变字段边界。"""
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

fam=collections.defaultdict(lambda: collections.Counter())
for x in inner:
    fam[x[0]][x]+=1

for f0 in sorted(fam):
    print("="*72)
    print("族 byte0=0x%02X : %d 样本, %d distinct"%(f0,sum(fam[f0].values()),len(fam[f0])))
    # 按长度排序输出 distinct
    items=sorted(fam[f0].items(), key=lambda kv:(len(kv[0]),kv[0]))
    for x,cnt in items:
        print("  len=%3d x%-3d  %s"%(len(x),cnt,x.hex()))
