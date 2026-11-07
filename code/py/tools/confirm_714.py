#!/usr/bin/env python3
"""确认: (1) 全语料 71/4 只有 nQlo 一个值? (2) 16字节 blob 全语料是否只此一份?
(3) 71/4 的 u32 值是否只有 31902622 一个? 跨 83 run 全恒定?"""
import json, collections, struct
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())

b1=collections.Counter(); b2=collections.Counter(); u=collections.Counter()
lens=collections.Counter()
for r in recs:
    if r.get("svc")==71 and r.get("task")==4:
        p=bytes.fromhex(r["payload"])
        lens[len(p)]+=1
        if len(p)>=22: b1[p[6:22]]+=1
        if len(p)>=44: b2[p[0x1c:0x2c]]+=1
        if len(p)>=49: u[struct.unpack_from("<I",p,45)[0]]+=1
print("71/4 长度分布:", dict(lens))
print("blob1 (16B) 值:", {k.decode('latin1'):v for k,v in b1.items()})
print("blob2 (16B) 值:", {k.decode('latin1'):v for k,v in b2.items()})
print("u32@45 值:", dict(u))

# 全语料搜 'nQlo' 与 '++++' 出现位置
print("\n=== 全语料搜 nQlo / ++++++++ ===")
for key in [b"nQloP0oCVWR6RDJS", b"++++++++++++++++"]:
    locs=collections.Counter()
    for r in recs:
        p=bytes.fromhex(r["payload"])
        if key in p:
            locs["%d/%d"%(r["svc"],r["task"])]+=1
    print("  %r -> %s" % (key, dict(locs)))
