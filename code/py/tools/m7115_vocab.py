#!/usr/bin/env python3
"""71/15 解压后事件词表 + 参数统计. 确认它是"压缩的遥测批". 收口 §七 #2 最后一项."""
import json, zlib, collections, re
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())
ps=[bytes.fromhex(r["payload"]) for r in recs if r.get("svc")==71 and r.get("task")==15]
names=collections.Counter(); pages=collections.Counter(); total_lines=0
for p in ps:
    idx=min([x for x in (p.find(b"\x78\x01"),p.find(b"\x78\x9c")) if x>=0] or [-1])
    if idx<0: continue
    dec=zlib.decompress(p[idx:])
    for line in dec.split(b"\n"):
        if not line: continue
        total_lines+=1
        parts=line.split(b"|")
        if parts: names[parts[0].decode("latin1")]+=1
        # UIPage 的最后一个参数 = 页面号
        if parts and parts[0]==b"UIPage":
            pages[parts[-1].decode("latin1")]+=1
print("71/15: %d 条, 解压后共 %d 行事件"%(len(ps),total_lines))
print("\n事件名:")
for n,c in names.most_common(): print("  %-24s x%d"%(n,c))
print("\nUIPage 页面号分布(前 20):",dict(pages.most_common(20)))
print("UIPage 页面号 distinct:",len(pages)," min/max:",min(pages,key=int),max(pages,key=int))
# 压缩头统计
heads=collections.Counter(p[min([x for x in (p.find(b'\x78\x01'),p.find(b'\x78\x9c')) if x>=0] or [0]):][:2].hex() for p in ps)
print("\nzlib 头:",dict(heads))
