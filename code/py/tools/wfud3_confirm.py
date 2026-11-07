#!/usr/bin/env python3
"""确认: 'wfUD3\"' 是否是我正则把 88 77 66 55 44 33 22 11 当 ASCII 的假阳性.
   扫全语料: 出现 wfUD3\" 字面的条数; 以及 88 77 66 55 44 33 22 11 的 true 二进制位置。
"""
import json, struct, collections
CORPUS=r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs=json.load(open(CORPUS,"r",encoding="utf-8"))
if isinstance(recs,dict): recs=recs.get("records") or recs.get("data") or list(recs.values())
lit=b'wfUD3"'
magic=bytes.fromhex("8877665544332211")
bytask_lit=collections.Counter()
bytask_magic=collections.Counter()
for r in recs:
    p=bytes.fromhex(r["payload"])
    if lit in p: bytask_lit[(r.get("svc"),r.get("task"))]+=1
    if magic in p: bytask_magic[(r.get("svc"),r.get("task"))]+=1
print("字面 'wfUD3\"' 出现在:",dict(bytask_lit) or "无")
print("真实字节 88 77 66 55 44 33 22 11 (魔数C) 出现在:",dict(bytask_magic))
print()
print("=> wfUD3\" 是 (0x77 'w')(0x66 'f')(0x55 'U')(0x44 'D')(0x33 '3')(0x22 '\"') 即魔数C小端段被正则当成 ASCII")
