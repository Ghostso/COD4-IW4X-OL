#!/usr/bin/env python3
"""71/15 解压: payload = 0x13 08 <u32 len> <zlib 78 01 ...>. 解压看内容(可能又是遥测文本)."""
import json, struct, zlib, collections
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())
ps=[bytes.fromhex(r["payload"]) for r in recs if r.get("svc")==71 and r.get("task")==15]
print("71/15 条数:",len(ps))
ok=0; fail=0
contents=collections.Counter()
for p in ps:
    # 找 zlib 起点 78 01 / 78 9c / 78 da
    idx=-1
    for sig in (b"\x78\x01",b"\x78\x9c",b"\x78\xda"):
        j=p.find(sig)
        if j>=0: idx=j;break
    if idx<0:
        fail+=1; continue
    try:
        dec=zlib.decompress(p[idx:])
        ok+=1
        contents[dec]+=1
    except Exception as e:
        fail+=1
print("解压成功 %d / 失败 %d"%(ok,fail))
print("解压后 distinct:",len(contents))
for dec,c in contents.most_common(6):
    print("\n  x%d len=%d:"%(c,len(dec)))
    print("   %r"%dec[:400])
