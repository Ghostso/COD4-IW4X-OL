#!/usr/bin/env python3
"""验证: 21/5 里 -695030357(i32) 与 0xD692ADAB(u32) 是同一字节串 0xAB AD 92 D6。
统计语料里该字节串在各 task 出现次数, 以及 i32/u32 两种读法。"""
import json, collections, struct
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())

TARGET=0xD692ADAB
LE=TARGET.to_bytes(4,'little')
print("0xD692ADAB 小端字节 =", LE.hex(), "(即 AB AD 92 D6)")

by=collections.Counter()
for r in recs:
    p=bytes.fromhex(r["payload"])
    n=p.count(LE)
    if n: by["%d/%d"%(r["svc"],r["task"])]+=n
print("\n字节串 AB AD 92 D6 在各 task 出现次数:")
for k in sorted(by): print("  %-8s x%d"%(k,by[k]))
print("总:", sum(by.values()))

# 21/5 详情: 每条有几个? i32 读法?
print("\n=== 21/5 记录里该值 ===")
cnt=0
for r in recs:
    if r.get("svc")==21 and r.get("task")==5:
        p=bytes.fromhex(r["payload"])
        idxs=[]
        i=0
        while True:
            j=p.find(LE,i)
            if j<0: break
            idxs.append(j); i=j+1
        if idxs:
            cnt+=1
            if cnt<=5:
                print("  len=%d 位置%s  i32=%d u32=%d"%(len(p),idxs,
                      struct.unpack_from("<i",p,idxs[0])[0], struct.unpack_from("<I",p,idxs[0])[0]))
print("21/5 含该值的记录数:", cnt)
